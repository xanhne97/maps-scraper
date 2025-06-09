import os
from serpapi import GoogleSearch
from math import radians, sin, cos, sqrt, asin

SERP_API_KEY = os.getenv("SERPAPI_API_KEY") or "fbfa3f1910e80bcea048aca735378f18771f79a42216962e95d1e12219820e6f"

def haversine(lat1, lon1, lat2, lon2):
    # Tính khoảng cách giữa 2 tọa độ theo đơn vị mét
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def scrape_from_keywords(keywords, lat, lng, street_filter=None, radius_m=None):
    all_results = []

    for keyword in keywords:
        params = {
            "engine": "google_maps",
            "type": "search",
            "q": keyword,
            "ll": f"@{lat},{lng},15z",
            "api_key": SERP_API_KEY
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results.get("local_results", [])

            print(f"🔍 {len(local_results)} kết quả cho từ khóa: {keyword}")

            for place in local_results:
                address = place.get("address", "")
                coords = place.get("gps_coordinates")

                if not address or not coords:
                    continue

                # ✅ Kiểm tra tên đường
                if street_filter and street_filter.lower() not in address.lower():
                    print(f"⛔ Bỏ qua (không chứa tên đường): {address}")
                    continue

                # ✅ Kiểm tra khoảng cách
                distance = haversine(lat, lng, coords["latitude"], coords["longitude"])
                if radius_m and distance > radius_m:
                    print(f"⛔ Bỏ qua (quá xa): {address} ({int(distance)}m)")
                    continue

                all_results.append({
                    "title": place.get("title"),
                    "address": address,
                    "phone": place.get("phone"),
                    "website": place.get("website"),
                    "lat": coords["latitude"],
                    "lng": coords["longitude"],
                    "distance": int(distance)
                })

        except Exception as e:
            print(f"❌ Lỗi với từ khóa '{keyword}': {e}")

    return all_results
