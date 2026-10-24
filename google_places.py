"""Tìm địa điểm bằng Google Places API (New) - Text Search."""
import os

import requests

API_URL = "https://places.googleapis.com/v1/places:searchText"
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

PAGE_SIZE = 20
MAX_PAGES = 3  # Text Search trả tối đa 60 kết quả (3 trang) cho một truy vấn

# Chỉ lấy các trường cần dùng: Google tính tiền theo trường được yêu cầu
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.rating",
    "places.userRatingCount",
    "places.primaryTypeDisplayName",
    "places.googleMapsUri",
    "places.businessStatus",
    "nextPageToken",
])


def _rectangle(rect):
    (low_lat, low_lng), (high_lat, high_lng) = rect
    return {
        "rectangle": {
            "low": {"latitude": low_lat, "longitude": low_lng},
            "high": {"latitude": high_lat, "longitude": high_lng},
        }
    }


def _normalize(p):
    loc = p.get("location") or {}
    return {
        "title": (p.get("displayName") or {}).get("text"),
        "category": (p.get("primaryTypeDisplayName") or {}).get("text"),
        "address": p.get("formattedAddress"),
        "phone": p.get("nationalPhoneNumber"),
        "website": p.get("websiteUri"),
        "rating": p.get("rating"),
        "reviews": p.get("userRatingCount"),
        "lat": loc.get("latitude"),
        "lng": loc.get("longitude"),
        "maps_url": p.get("googleMapsUri"),
        "source": "Google",
        "_id": f"g:{p['id']}",
    }


def search(keyword, pages, rect=None, center=None):
    """Tìm một từ khóa trong khung rect ((low_lat, low_lng), (high_lat, high_lng)).

    Không có rect thì ưu tiên (không bắt buộc) quanh center.
    Trả về (danh sách địa điểm, số lượt gọi API đã dùng).
    """
    if not API_KEY:
        raise RuntimeError("Chưa cấu hình biến môi trường GOOGLE_MAPS_API_KEY")

    body = {"textQuery": keyword, "languageCode": "vi", "regionCode": "VN", "pageSize": PAGE_SIZE}
    if rect:
        body["locationRestriction"] = _rectangle(rect)
    elif center:
        body["locationBias"] = {
            "circle": {"center": {"latitude": center[0], "longitude": center[1]}, "radius": 5000.0}
        }
    headers = {"X-Goog-Api-Key": API_KEY, "X-Goog-FieldMask": FIELD_MASK}

    places, calls = [], 0
    for _ in range(min(pages, MAX_PAGES)):
        resp = requests.post(API_URL, json=body, headers=headers, timeout=30)
        calls += 1
        data = resp.json() if resp.content else {}
        if resp.status_code != 200:
            message = (data.get("error") or {}).get("message") or resp.text[:200]
            error = RuntimeError(f"Google Places lỗi {resp.status_code}: {message}")
            error.calls = calls  # để bộ đếm quota vẫn tính các lượt đã gọi
            raise error

        places.extend(
            _normalize(p) for p in data.get("places", [])
            if p.get("businessStatus") != "CLOSED_PERMANENTLY"
        )
        token = data.get("nextPageToken")
        if not token:
            break
        body["pageToken"] = token
    return places, calls
