import os
from serpapi import GoogleSearch
from geopy.distance import geodesic

# Lấy API key từ biến môi trường hoặc giá trị mặc định (nên đặt biến môi trường SERPAPI_API_KEY trên Render)
SERP_API_KEY = os.getenv("SERPAPI_API_KEY") or "fbfa3f1910e80bcea048aca735378f18771f79a42216962e95d1e12219820e6f"

# Vị trí trung tâm (toạ độ giả định, có thể chỉnh theo từng thành phố hoặc theo input người dùng)
CENTER_COORDS = (10.7769, 106.7009)  # TP.HCM


def scrape_from_keywords(keywords, street_filter=None, radius_km=None):
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

            if not local_results:
                print(f"⚠️ Không có kết quả cho từ khóa: {keyword}")
            else:
                print(f"✅ Tìm thấy {len(local_results)} kết quả cho: {keyword}")

            for item in local_results:
                address = item.get("address")
                coords = item.get("gps_coordinates")

                # Lọc theo tên đường nếu có
                if street_filter and (not address or street_filter.lower() not in address.lower()):
                    continue

                # Lọc theo bán kính nếu có
                if radius_km and coords:
                    place_coords = (coords.get("latitude"), coords.get("longitude"))
                    distance = geodesic(CENTER_COORDS, place_coords).km
                    if distance > radius_km:
                        continue

                all_results.append({
                    "title": item.get("title"),
                    "address": address,
                    "phone": item.get("phone"),
                    "website": item.get("website"),
                    "lat": coords.get("latitude") if coords else None,
                    "lng": coords.get("longitude") if coords else None,
                })

        except Exception as e:
            print(f"❌ Lỗi với từ khóa '{keyword}': {e}")

    return all_results
