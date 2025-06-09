import os
from serpapi import GoogleSearch
from geopy.distance import geodesic

# API KEY từ biến môi trường (hoặc backup key nếu test)
SERP_API_KEY = os.getenv("SERPAPI_API_KEY") or "YOUR_BACKUP_KEY"

def scrape_from_keywords(keywords, lat=None, lng=None, street_filter=None, radius_km=None):
    all_results = []

    if not lat or not lng:
        print("⚠️ Chưa có toạ độ trung tâm, không thể tìm kiếm theo khu vực.")
        return []

    center_coords = (float(lat), float(lng))

    for keyword in keywords:
        print(f"🔍 Đang tìm: {keyword} quanh {center_coords}...")

        params = {
            "engine": "google_maps",
            "q": keyword,
            "ll": f"@{center_coords[0]},{center_coords[1]},10z",  # zoom mặc định cấp quận
            "type": "search",
            "api_key": SERP_API_KEY
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results.get("local_results", [])

            print(f"✅ Tìm thấy {len(local_results)} kết quả cho từ khóa: {keyword}")

            for item in local_results:
                address = item.get("address", "")
                coords = item.get("gps_coordinates")

                if not coords:
                    print(f"⚠️ Bỏ qua (không có tọa độ): {address}")
                    continue

                # Lọc theo tên đường
                if street_filter and street_filter.lower() not in address.lower():
                    print(f"⛔ Bỏ qua (không chứa tên đường): {address}")
                    continue

                # Lọc theo bán kính
                place_coords = (coords.get("latitude"), coords.get("longitude"))
                distance = geodesic(center_coords, place_coords).m
                if radius_km and distance > radius_km * 1000:
                    print(f"⛔ Bỏ qua (quá xa - {distance:.0f}m): {address}")
                    continue

                all_results.append({
                    "title": item.get("title"),
                    "address": address,
                    "phone": item.get("phone"),
                    "website": item.get("website"),
                    "lat": place_coords[0],
                    "lng": place_coords[1],
                    "distance_m": int(distance)
                })

        except Exception as e:
            print(f"❌ Lỗi với từ khóa '{keyword}': {e}")

    return all_results
