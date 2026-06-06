import os
from serpapi import GoogleSearch
from geopy.distance import geodesic

# Lấy API key từ biến môi trường hoặc giá trị mặc định (nên đặt biến môi trường SERPAPI_API_KEY trên Render)
SERP_API_KEY = os.getenv("SERPAPI_API_KEY") or "fbfa3f1910e80bcea048aca735378f18771f79a42216962e95d1e12219820e6f"

# Vị trí trung tâm mặc định (có thể thay đổi theo input người dùng)
CENTER_COORDS = (10.9501, 106.8167)  # Ví dụ: Biên Hòa

def scrape_from_keywords(keywords, center_coords=CENTER_COORDS, radius_m=None):
    all_results = []

    for keyword in keywords:
        params = {
            "engine": "google_maps",
            "q": keyword,
            "ll": f"@{center_coords[0]},{center_coords[1]},14z",  # zoom cấp 14 theo tọa độ
            "type": "search",
            "api_key": SERP_API_KEY
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results.get("local_results", [])

            if not local_results:
                print(f"⚠️ Không có kết quả cho từ khóa: {keyword}")
            else:
                print(f"✅ Tìm thấy {len(local_results)} kết quả cho: {keyword}")

            for item in local_results:
                address = item.get("address")
                coords = item.get("gps_coordinates")

                distance = None
                if radius_m and coords:
                    place_coords = (coords.get("latitude"), coords.get("longitude"))
                    distance = geodesic(center_coords, place_coords).meters
                    if distance > radius_m:
                        continue

                all_results.append({
                    "title": item.get("title"),
                    "address": address,
                    "phone": item.get("phone"),
                    "website": item.get("website"),
                    "lat": coords.get("latitude") if coords else None,
                    "lng": coords.get("longitude") if coords else None,
                    "distance": distance
                })

        except Exception as e:
            print(f"❌ Lỗi với từ khóa '{keyword}': {e}")

    return all_results
