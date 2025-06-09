import os
from serpapi import GoogleSearch

# Lấy API Key từ biến môi trường, hoặc fallback key mặc định
SERP_API_KEY = os.getenv("SERPAPI_API_KEY") or "fbfa3f1910e80bcea048aca735378f18771f79a42216962e95d1e12219820e6f"

def scrape_from_keywords(keywords, max_results=40):
    all_results = []

    for keyword in keywords:
        params = {
            "engine": "google_maps",
            "q": keyword,
            "location": "Vietnam",       # Gợi ý để SerpAPI xác định khu vực
            "type": "search",
            "api_key": SERP_API_KEY,
            "num": max_results           # ✅ Số lượng kết quả mong muốn (tối đa 120 tùy plan)
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
