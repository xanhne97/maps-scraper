import os
from serpapi import GoogleSearch
from geopy.distance import geodesic

# Lấy API key từ biến môi trường (khuyến khích) hoặc fallback thủ công
SERP_API_KEY = os.getenv("SERPAPI_API_KEY") or "fbfa3f1910e80bcea048aca735378f18771f79a42216962e95d1e12219820e6f"

def scrape_from_keywords(keywords, street_filter=None, radius_km=None, center_coords=None):
    all_results = []

    for keyword in keywords:
        params = {
            "engine": "google_maps",
            "q": keyword,
            "location": "Vietnam",
            "type": "search",
            "api_key": SERP_API_KEY
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results.get("local_results", [])

            print(f"🔍 Từ khóa: {keyword} — Kết quả: {len(local_results)}")

            for item in local_results:
                address = item.get("address", "")
                coords = item.get("gps_coordinates")

                # ✅ Lọc theo tên đường nếu được yêu cầu
                if street_filter and street_filter.lower() not in address.lower():
                    print(f"⛔ Bỏ qua (không chứa tên đường): {address}")
                    continue

                # ✅ Lọc theo bán kính nếu được yêu cầu
                if radius_km and coords and center_coords:
                    place_coords = (coords.get("latitude"), coords.get("longitude"))
                    distance = geodesic(center_coords, place_coords).km
                    if distance > radius_km:
                        print(f"⛔ Bỏ qua (vượt bán kính {radius_km}km): {distance:.2f} km — {address}")
                        continue

                # ✅ Nếu qua tất cả lọc thì thêm vào kết quả
                all_results.append({
                    "title": item.get("title"),
                    "address": address,
                    "phone": item.get("phone"),
                    "website": item.get("website"),
                    "lat": coords.get("latitude") if coords else None,
                    "lng": coords.get("longitude") if coords else None,
                })

        except Exception as e:
            print(f"❌ Lỗi khi tìm '{keyword}': {e}")

    return all_results
