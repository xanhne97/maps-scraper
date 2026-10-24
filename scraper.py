import math
import os
from concurrent.futures import ThreadPoolExecutor

from geopy.distance import geodesic
from serpapi import GoogleSearch

# API key chỉ lấy từ biến môi trường (đặt SERPAPI_API_KEY trên Render), không ghi vào code
SERP_API_KEY = os.getenv("SERPAPI_API_KEY")

PAGE_SIZE = 20          # Google Maps trả tối đa 20 kết quả mỗi trang
MAX_PAGES = 6           # SerpAPI khuyến nghị start tối đa 100 (= 6 trang)
MAX_WORKERS = 8         # số request gọi song song
MAX_API_CALLS = 200     # trần số lượt gọi cho một lần tìm, tránh cháy quota
MAX_GRID_POINTS = 25    # số điểm lưới tối đa khi quét sâu
BASE_CELL_RADIUS = 1000 # bán kính mỗi ô lưới (mét) khi bán kính tìm còn nhỏ

# Mức độ quét: số trang tối đa cho mỗi điểm, có chia vùng thành lưới hay không
SCAN_LEVELS = {
    "fast": {"label": "Nhanh", "pages": 1, "grid": False},
    "normal": {"label": "Vừa", "pages": 3, "grid": False},
    "deep": {"label": "Sâu (chia lưới)", "pages": 3, "grid": True},
}

# Vị trí trung tâm mặc định (Biên Hòa)
CENTER_COORDS = (10.9501, 106.8167)


def zoom_for_radius(radius_m):
    """Chọn mức zoom sao cho khung bản đồ vừa phủ bán kính cần tìm."""
    if not radius_m:
        return 14
    for limit, zoom in ((300, 17), (600, 16), (1200, 15), (2500, 14), (5000, 13), (10000, 12), (20000, 11)):
        if radius_m <= limit:
            return zoom
    return 10


def _offset(center, dx_m, dy_m):
    lat, lng = center
    return (
        lat + dy_m / 111320,
        lng + dx_m / (111320 * math.cos(math.radians(lat))),
    )


def build_grid(center, radius_m):
    """Chia vùng tròn thành lưới điểm, mỗi điểm là một lượt tìm riêng.

    Google Maps chỉ trả về ~120 kết quả cho một khung nhìn, nên tìm ở nhiều
    điểm nhỏ trong vùng sẽ ra được nhiều cơ sở hơn tìm một lần ở tâm.
    Trả về (danh sách điểm, bán kính mỗi ô).
    """
    spacing = BASE_CELL_RADIUS * math.sqrt(2)
    while True:
        n = int(radius_m // spacing)
        points = []
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                dx, dy = i * spacing, j * spacing
                if math.hypot(dx, dy) <= radius_m + spacing / 2:
                    points.append(_offset(center, dx, dy))
        if len(points) <= MAX_GRID_POINTS:
            return points, spacing / math.sqrt(2)
        spacing *= 1.2


def plan_search(keywords, center, radius_m, level):
    """Tính trước các điểm tìm, zoom và số trang để không vượt MAX_API_CALLS."""
    cfg = SCAN_LEVELS.get(level, SCAN_LEVELS["normal"])
    if cfg["grid"] and radius_m and radius_m > BASE_CELL_RADIUS:
        points, cell_radius = build_grid(center, radius_m)
    else:
        points, cell_radius = [center], radius_m
    zoom = zoom_for_radius(cell_radius)

    chains = len(points) * len(keywords)
    if chains > MAX_API_CALLS:
        raise ValueError(
            f"Cần ít nhất {chains} lượt gọi API (tối đa {MAX_API_CALLS}). "
            "Hãy giảm số từ khóa, giảm bán kính hoặc chọn mức quét thấp hơn."
        )
    pages = max(1, min(cfg["pages"], MAX_PAGES, MAX_API_CALLS // chains))
    return points, zoom, pages


def _fetch_page(keyword, point, zoom, start):
    params = {
        "engine": "google_maps",
        "type": "search",
        "q": keyword,
        "ll": f"@{point[0]},{point[1]},{zoom}z",
        "start": start,
        "hl": "vi",
        "api_key": SERP_API_KEY,
    }
    res = GoogleSearch(params).get_dict()
    error = res.get("error")
    if error:
        if "hasn't returned any results" in error:
            return [], False
        raise RuntimeError(error)

    items = res.get("local_results") or []
    # Khi từ khóa khớp đúng một địa điểm, SerpAPI trả place_results thay vì danh sách
    if not items and res.get("place_results"):
        items = [res["place_results"]]
    has_next = len(items) >= PAGE_SIZE and bool(res.get("serpapi_pagination", {}).get("next"))
    return items, has_next


def _scan_chain(keyword, point, zoom, pages, center, radius_m):
    """Lật lần lượt các trang cho một (từ khóa, điểm). Trả về (items, số lượt gọi, lỗi)."""
    items, calls = [], 0
    try:
        for page in range(pages):
            page_items, has_next = _fetch_page(keyword, point, zoom, page * PAGE_SIZE)
            calls += 1
            items.extend((keyword, it) for it in page_items)
            if not has_next:
                break
            # Trang này toàn chỗ nằm ngoài bán kính thì các trang sau còn xa hơn, dừng sớm
            if radius_m and not any(_in_radius(it, center, radius_m) for it in page_items):
                break
    except Exception as e:
        return items, calls, f"'{keyword}' tại ({point[0]:.4f}, {point[1]:.4f}): {e}"
    return items, calls, None


def _coords(item):
    c = item.get("gps_coordinates") or {}
    lat, lng = c.get("latitude"), c.get("longitude")
    return (lat, lng) if lat is not None and lng is not None else None


def _in_radius(item, center, radius_m):
    coords = _coords(item)
    return coords is not None and geodesic(center, coords).meters <= radius_m


def _normalize(item, keyword, center):
    coords = _coords(item)
    place_id = item.get("place_id")
    return {
        "title": item.get("title"),
        "category": item.get("type"),
        "address": item.get("address"),
        "phone": item.get("phone"),
        "website": item.get("website"),
        "rating": item.get("rating"),
        "reviews": item.get("reviews"),
        "lat": coords[0] if coords else None,
        "lng": coords[1] if coords else None,
        "distance": round(geodesic(center, coords).meters) if coords else None,
        "maps_url": f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else None,
        "keywords": keyword,
        "_key": place_id or item.get("data_id") or f"{item.get('title')}|{item.get('address')}",
    }


def scrape_from_keywords(keywords, center_coords=CENTER_COORDS, radius_m=None, level="normal"):
    """Tìm theo nhiều từ khóa, gộp trùng, lọc theo bán kính và sắp theo khoảng cách.

    Trả về dict gồm results (danh sách địa điểm) và stats (thống kê lượt tìm).
    """
    if not SERP_API_KEY:
        raise RuntimeError("Chưa cấu hình biến môi trường SERPAPI_API_KEY")

    points, zoom, pages = plan_search(keywords, center_coords, radius_m, level)
    jobs = [(kw, p) for kw in keywords for p in points]

    raw, errors, api_calls = [], [], 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [
            pool.submit(_scan_chain, kw, p, zoom, pages, center_coords, radius_m)
            for kw, p in jobs
        ]
        for f in futures:
            items, calls, error = f.result()
            raw.extend(items)
            api_calls += calls
            if error:
                errors.append(error)

    merged = {}
    for keyword, item in raw:
        place = _normalize(item, keyword, center_coords)
        if radius_m and (place["distance"] is None or place["distance"] > radius_m):
            continue
        existing = merged.get(place["_key"])
        if existing:
            if keyword not in existing["keywords"].split(", "):
                existing["keywords"] += f", {keyword}"
        else:
            merged[place["_key"]] = place

    results = sorted(
        merged.values(),
        key=lambda p: (p["distance"] is None, p["distance"] or 0),
    )
    for p in results:
        del p["_key"]

    print(f"✅ {len(results)} địa điểm / {len(raw)} kết quả thô / {api_calls} lượt gọi API")
    return {
        "results": results,
        "stats": {
            "api_calls": api_calls,
            "raw_count": len(raw),
            "unique_count": len(results),
            "points": len(points),
            "pages": pages,
            "zoom": zoom,
        },
        "errors": errors,
    }
