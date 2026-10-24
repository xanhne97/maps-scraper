import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

from geopy.distance import geodesic

import cache
import google_places
import osm

MAX_WORKERS = 8         # số request Google gọi song song
MAX_API_CALLS = 200     # trần số lượt gọi Google cho một lần tìm
MAX_GRID_TILES = 25     # số ô lưới tối đa khi quét sâu
BASE_TILE_SIZE = 1500   # cạnh mỗi ô lưới (mét) khi bán kính tìm còn nhỏ
MERGE_DISTANCE = 150    # hai kết quả Google/OSM cách nhau dưới mức này và trùng tên thì coi là một

# Giới hạn lượt gọi Google mỗi tháng, đặt theo hạn mức miễn phí trên bảng giá Google Cloud
GOOGLE_MONTHLY_LIMIT = int(os.getenv("GOOGLE_MONTHLY_LIMIT", "1000"))

# Mức độ quét: số trang tối đa cho mỗi ô, có chia vùng thành lưới hay không
SCAN_LEVELS = {
    "fast": {"label": "Nhanh", "pages": 1, "grid": False},
    "normal": {"label": "Vừa", "pages": 3, "grid": False},
    "deep": {"label": "Sâu (chia lưới)", "pages": 3, "grid": True},
}

# Vị trí trung tâm mặc định (Biên Hòa)
CENTER_COORDS = (10.9501, 106.8167)


def _offset(center, dx_m, dy_m):
    lat, lng = center
    return (
        lat + dy_m / 111320,
        lng + dx_m / (111320 * math.cos(math.radians(lat))),
    )


def _rect(center, half_m):
    return _offset(center, -half_m, -half_m), _offset(center, half_m, half_m)


def build_tiles(center, radius_m):
    """Chia vùng tròn thành các ô vuông liền nhau, mỗi ô là một lượt tìm riêng.

    Google chỉ trả tối đa 60 kết quả cho một truy vấn, nên tìm trong nhiều ô nhỏ
    sẽ ra được nhiều cơ sở hơn tìm một lần cho cả vùng.
    """
    size = BASE_TILE_SIZE
    while True:
        n = math.ceil(radius_m / size)
        tiles = []
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                dx, dy = i * size, j * size
                # giữ ô nếu có phần giao với vòng tròn
                if math.hypot(dx, dy) - size / math.sqrt(2) <= radius_m:
                    tiles.append(_rect(_offset(center, dx, dy), size / 2))
        if len(tiles) <= MAX_GRID_TILES:
            return tiles
        size *= 1.2


def plan_search(keywords, center, radius_m, level):
    """Tính trước các ô tìm và số trang để không vượt MAX_API_CALLS."""
    cfg = SCAN_LEVELS.get(level, SCAN_LEVELS["normal"])
    if cfg["grid"] and radius_m and radius_m > BASE_TILE_SIZE / 2:
        tiles = build_tiles(center, radius_m)
    elif radius_m:
        tiles = [_rect(center, radius_m)]
    else:
        tiles = [None]

    chains = len(tiles) * len(keywords)
    if chains > MAX_API_CALLS:
        raise ValueError(
            f"Cần ít nhất {chains} lượt gọi API (tối đa {MAX_API_CALLS}). "
            "Hãy giảm số từ khóa, giảm bán kính hoặc chọn mức quét thấp hơn."
        )
    pages = max(1, min(cfg["pages"], google_places.MAX_PAGES, MAX_API_CALLS // chains))
    return tiles, pages


def _round_rect(rect):
    return [[round(v, 5) for v in corner] for corner in rect] if rect else None


def _google_job(keyword, rect, pages, center):
    try:
        places, calls = google_places.search(keyword, pages, rect=rect, center=center)
        return keyword, places, calls, None
    except Exception as e:
        return keyword, [], getattr(e, "calls", 0), f"Google '{keyword}': {e}"


def _osm_job(keywords, center, radius_m, refresh):
    key = cache.make_key("osm", {
        "q": sorted(kw.lower() for kw in keywords),
        "c": [round(v, 4) for v in center],
        "r": radius_m,
    })
    found = None if refresh else cache.get(key)
    if found is None:
        try:
            found = osm.search(keywords, center, radius_m)
        except Exception as e:
            return [], [str(e)]
        cache.set(key, found)
    return [(kw, place) for kw, place in found], []


def _name_key(name):
    return re.sub(r"[^a-z0-9]+", " ", osm.unaccent((name or "").lower())).strip()


def _same_name(a, b):
    a, b = _name_key(a), _name_key(b)
    if not a or not b:
        return False
    return a in b or b in a or SequenceMatcher(None, a, b).ratio() >= 0.75


def _quick_distance(a, b):
    """Khoảng cách xấp xỉ (mét), đủ chính xác cho vài trăm mét và nhanh hơn geodesic."""
    dy = (a["lat"] - b["lat"]) * 111320
    dx = (a["lng"] - b["lng"]) * 111320 * math.cos(math.radians(a["lat"]))
    return math.hypot(dx, dy)


def _merge(google_found, osm_found, center, radius_m):
    merged = {}

    def add(keyword, place):
        existing = merged.get(place["_id"])
        if existing:
            if keyword not in existing["keywords"].split(", "):
                existing["keywords"] += f", {keyword}"
            return
        has_coords = place["lat"] is not None and place["lng"] is not None
        place["distance"] = round(geodesic(center, (place["lat"], place["lng"])).meters) if has_coords else None
        if radius_m and (place["distance"] is None or place["distance"] > radius_m):
            return
        place["keywords"] = keyword
        merged[place["_id"]] = place

    for keyword, place in google_found:
        add(keyword, dict(place))

    google_list = [p for p in merged.values() if p["lat"] is not None]
    for keyword, place in osm_found:
        place = dict(place)
        if place["lat"] is not None:
            twin = next(
                (g for g in google_list
                 if _quick_distance(g, place) <= MERGE_DISTANCE and _same_name(g["title"], place["title"])),
                None,
            )
            if twin:
                # Cùng một cơ sở: giữ bản Google, lấy thêm thông tin còn thiếu từ OSM
                twin["phone"] = twin["phone"] or place["phone"]
                twin["website"] = twin["website"] or place["website"]
                twin["source"] = "Google + OSM"
                if keyword not in twin["keywords"].split(", "):
                    twin["keywords"] += f", {keyword}"
                continue
        add(keyword, place)

    results = sorted(merged.values(), key=lambda p: (p["distance"] is None, p["distance"] or 0))
    for p in results:
        del p["_id"]
    return results


def scrape_from_keywords(keywords, center_coords=CENTER_COORDS, radius_m=None, level="normal",
                         use_osm=True, refresh=False):
    """Tìm theo nhiều từ khóa từ Google Places và OpenStreetMap, có cache.

    Trả về dict gồm results (danh sách địa điểm), stats và errors.
    """
    use_google = bool(google_places.API_KEY)
    if not use_google and not use_osm:
        raise RuntimeError("Chưa cấu hình GOOGLE_MAPS_API_KEY, hãy bật nguồn OpenStreetMap hoặc đặt key")
    errors = [] if use_google else ["Chưa cấu hình GOOGLE_MAPS_API_KEY, chỉ tìm trên OpenStreetMap"]

    google_found, jobs, cache_hits = [], [], 0
    tiles, pages = [], 0
    if use_google:
        tiles, pages = plan_search(keywords, center_coords, radius_m, level)
        for kw in keywords:
            for rect in tiles:
                key = cache.make_key("google", {
                    "q": kw.lower(),
                    "rect": _round_rect(rect),
                    "c": None if rect else [round(v, 4) for v in center_coords],
                    "pages": pages,
                })
                places = None if refresh else cache.get(key)
                if places is None:
                    jobs.append((kw, rect, key))
                else:
                    cache_hits += 1
                    google_found.extend((kw, p) for p in places)

        max_calls = len(jobs) * pages
        used = cache.monthly_usage()
        if used + max_calls > GOOGLE_MONTHLY_LIMIT:
            raise ValueError(
                f"Tháng này đã dùng {used}/{GOOGLE_MONTHLY_LIMIT} lượt Google, lần tìm này có thể cần thêm "
                f"tối đa {max_calls} lượt. Hãy chọn mức quét thấp hơn hoặc tăng GOOGLE_MONTHLY_LIMIT."
            )

    api_calls, osm_found = 0, []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS + 1) as pool:
        osm_future = pool.submit(_osm_job, keywords, center_coords, radius_m, refresh) if use_osm else None
        futures = {pool.submit(_google_job, kw, rect, pages, center_coords): key for kw, rect, key in jobs}
        for future, key in futures.items():
            keyword, places, calls, error = future.result()
            api_calls += calls
            if error:
                errors.append(error)
            else:
                cache.set(key, places)
                google_found.extend((keyword, p) for p in places)
        if osm_future:
            osm_found, osm_errors = osm_future.result()
            errors.extend(osm_errors)

    cache.add_usage(api_calls)
    results = _merge(google_found, osm_found, center_coords, radius_m)

    print(f"✅ {len(results)} địa điểm / Google {len(google_found)} (gọi {api_calls}, cache {cache_hits}) / OSM {len(osm_found)}")
    return {
        "results": results,
        "stats": {
            "api_calls": api_calls,
            "cache_hits": cache_hits,
            "google_count": len(google_found),
            "osm_count": len(osm_found),
            "unique_count": len(results),
            "tiles": len(tiles),
            "pages": pages,
            "monthly_used": cache.monthly_usage() if use_google else None,
            "monthly_limit": GOOGLE_MONTHLY_LIMIT,
        },
        "errors": errors,
    }
