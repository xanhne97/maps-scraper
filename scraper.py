import os
from serpapi import GoogleSearch

# Đúng cú pháp lấy biến môi trường
SERP_API_KEY = os.getenv("SERPAPI_API_KEY") or "4d1768c9601cd2fb5b7e78d33f981521d07751a2a73e34fe31e09865e86a9be8"

def scrape_from_keywords(keywords):
    all_results = []

    for keyword in keywords:
        params = {
            "engine": "google_maps",
            "q": keyword,
            "location": "Vietnam",  # Gợi ý thêm để tăng độ chính xác
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
                all_results.append({
                    "title": item.get("title"),
                    "address": item.get("address"),
                    "phone": item.get("phone"),
                    "website": item.get("website"),
                })

        except Exception as e:
            print(f"❌ Lỗi với từ khóa '{keyword}': {e}")

    return all_results
