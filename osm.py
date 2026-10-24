"""Tìm địa điểm miễn phí từ OpenStreetMap qua Overpass API (không cần key)."""
import math
import re
import unicodedata

import requests

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "npoil-maps-scraper/1.0"}
DEFAULT_RADIUS = 3000

# OSM không tìm được theo chữ tự do, nên ánh xạ từ khóa thường gặp sang thẻ OSM.
# Xét theo thứ tự, dừng ở nhóm khớp đầu tiên (vd "rửa xe ô tô" chỉ là car_wash).
TAG_HINTS = [
    (("rua xe",), [("amenity", "car_wash")]),
    (("cay xang", "xang", "tram xang"), [("amenity", "fuel")]),
    (("nhot", "phu tung", "dau may"), [("shop", "car_parts"), ("shop", "motorcycle_parts")]),
    (("lop xe", "vo xe", "lop o to"), [("shop", "tyres")]),
    (("xe may", "honda", "moto"), [("shop", "motorcycle_repair"), ("shop", "motorcycle")]),
    (("o to", "oto", "xe hoi", "garage", "gara"), [("shop", "car_repair"), ("shop", "car")]),
]

CATEGORY_LABELS = {
    "car_wash": "Rửa xe",
    "fuel": "Cây xăng",
    "car_parts": "Phụ tùng ô tô",
    "motorcycle_parts": "Phụ tùng xe máy",
    "tyres": "Lốp xe",
    "motorcycle_repair": "Sửa xe máy",
    "motorcycle": "Cửa hàng xe máy",
    "car_repair": "Sửa ô tô",
    "car": "Đại lý ô tô",
}

ADDRESS_PARTS = ["addr:quarter", "addr:subdistrict", "addr:district", "addr:city", "addr:province"]


def unaccent(text):
    text = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _name_variants(keyword):
    # Bỏ ký tự đặc biệt thay vì escape, vì chuỗi Overpass và regex escape khác nhau
    forms = (keyword.lower(), unaccent(keyword.lower()))
    return sorted(v for v in {re.sub(r"[^\w\s]", " ", f).strip() for f in forms} if v)


def _hint_tags(keyword):
    plain = unaccent(keyword.lower())
    for terms, tags in TAG_HINTS:
        if any(re.search(rf"\b{t}\b", plain) for t in terms):
            return tags
    return []


def build_query(keywords, center, radius_m):
    """Gộp mọi từ khóa vào một truy vấn: máy chủ Overpass công cộng chậm, mỗi truy vấn mất vài chục giây."""
    # Lọc theo khung chữ nhật (có chỉ mục, nhanh hơn around); phần ngoài bán kính được loại khi gộp kết quả
    dlat = radius_m / 111320
    dlng = radius_m / (111320 * math.cos(math.radians(center[0])))
    bbox = f"{center[0] - dlat},{center[1] - dlng},{center[0] + dlat},{center[1] + dlng}"

    pattern = "|".join(dict.fromkeys(v for kw in keywords for v in _name_variants(kw)))
    # Chỉ dò tên trong các điểm kinh doanh (có thẻ shop/amenity/craft) để truy vấn nhanh
    filters = [f'nwr["{key}"]["name"~"{pattern}",i];' for key in ("shop", "amenity", "craft")]
    tags = dict.fromkeys(t for kw in keywords for t in _hint_tags(kw))
    filters += [f'nwr["{k}"="{v}"];' for k, v in tags]

    return f"[out:json][timeout:80][bbox:{bbox}];({''.join(filters)});out tags center;"


def _matching_keywords(tags, keywords):
    name = unaccent(tags.get("name", "").lower())
    return [
        kw for kw in keywords
        if any(v in name for v in map(unaccent, _name_variants(kw)))
        or any(tags.get(k) == v for k, v in _hint_tags(kw))
    ]


def _address(tags):
    if tags.get("addr:full"):
        return tags["addr:full"]
    street = " ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street")]))
    parts = [street] + [tags.get(k) for k in ADDRESS_PARTS]
    return ", ".join(p for p in parts if p) or None


def _normalize(el):
    tags = el.get("tags", {})
    lat = el.get("lat", (el.get("center") or {}).get("lat"))
    lng = el.get("lon", (el.get("center") or {}).get("lon"))
    kind = tags.get("shop") or tags.get("amenity") or tags.get("craft")
    return {
        "title": tags.get("name"),
        "category": CATEGORY_LABELS.get(kind, kind),
        "address": _address(tags),
        "phone": tags.get("phone") or tags.get("contact:phone"),
        "website": tags.get("website") or tags.get("contact:website"),
        "rating": None,
        "reviews": None,
        "lat": lat,
        "lng": lng,
        "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lng}" if lat is not None else None,
        "source": "OSM",
        "_id": f"o:{el['type']}/{el['id']}",
    }


def search(keywords, center, radius_m=None):
    """Tìm theo tên chứa từ khóa và theo loại hình tương ứng trong bán kính.

    Trả về danh sách (từ khóa, địa điểm); một địa điểm khớp nhiều từ khóa sẽ xuất hiện nhiều lần.
    """
    query = build_query(keywords, center, radius_m or DEFAULT_RADIUS)
    last_error = None
    for url in ENDPOINTS:
        try:
            resp = requests.post(url, data={"data": query}, headers=HEADERS, timeout=90)
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
            break
        except Exception as e:
            last_error = e
    else:
        raise RuntimeError(f"OpenStreetMap lỗi: {last_error}")

    found = []
    for el in elements:
        tags = el.get("tags", {})
        if not tags.get("name"):
            continue
        place = _normalize(el)
        found.extend((kw, place) for kw in _matching_keywords(tags, keywords) or keywords[:1])
    return found
