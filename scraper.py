import os
from serpapi import GoogleSearch
from geopy.distance import geodesic

# API Key lấy từ biến môi trường hoặc fallback
SERP_API_KEY = os.getenv("SERPAPI_API_KEY") or "YOUR_API_KEY_HERE"

def scrape_from_keywords(keywords, street_filter=None, radius_km=None, center_lat=None, center_lng=None):
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

            print(f"✅ {len(local_results)} kết quả cho từ khóa: {keyword}")

            for item in local_results:
                address = item.get("address", "")
                coords = item.get("gps_coordinates", {})

                # ✅ Bỏ qua nếu không có địa chỉ hoặc địa chỉ không chứa tên đường (nếu có yêu cầu)
                if street_filter and (street_filter.lower() not in address.lower()):
                    print(f"🚫 Bỏ qua (không chứa tên đường): {address}")
                    continue

                # ✅ Lọc theo bán kính nếu có toạ độ trung tâm và toạ độ địa điểm
                if radius_km and coords:
                    try:
                        place_coords = (coords.get("latitude"), coords.get("longitude"))
                        center_coords = (float(center_lat), float(center_lng))
                        distance_km = geodesic(center_coords, place_coords).km
                        if distance_km > radius_km:
                            print(f"📏 Ngoài bán kính: {distance_km:.2f} km > {radius_km} km")
                            continue
                    except Exception as ge:
                        print(f"⚠️ Lỗi đo khoảng cách: {ge}")

                all_results.append({
                    "title": item.get("title"),
                    "address": address,
                    "phone": item.get("phone"),
                    "website": item.get("website"),
                    "lat": coords.get("latitude"),
                    "lng": coords.get("longitude")
                })

        except Exception as e:
            print(f"❌ Lỗi khi tìm kiếm '{keyword}': {e}")

    return all_results
