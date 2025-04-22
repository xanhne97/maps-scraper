from serpapi import GoogleSearch

SERPAPI_KEY = "4d1768c9601cd2fb5b7e78d33f981521d07751a2a73e34fe31e09865e86a9be8"  # 👈 Thay bằng API key thật của bạn

def scrape_from_keywords(keywords):
    all_results = []

    for keyword in keywords:
        params = {
            "engine": "google_maps",
            "q": keyword,
            "type": "search",
            "api_key": SERPAPI_KEY
        }
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            places = results.get("local_results", [])

            for place in places:
                all_results.append({
                    "name": place.get("title"),
                    "address": place.get("address"),
                    "phone": place.get("phone"),
                    "website": place.get("website"),
                    "email": None  # SerpAPI không cung cấp email
                })
        except Exception as e:
            print(f"❌ Lỗi với từ khóa '{keyword}': {e}")
            continue

    return all_results
