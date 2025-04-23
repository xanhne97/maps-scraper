import os
from google_search_results import GoogleSearch

SERP_API_KEY = os.getenv("4d1768c9601cd2fb5b7e78d33f981521d07751a2a73e34fe31e09865e86a9be8")  # Bạn phải set biến môi trường này trên Render

def scrape_from_keywords(keywords):
    all_results = []

    for keyword in keywords:
        params = {
            "engine": "google_maps",
            "q": keyword,
            "type": "search",
            "api_key": SERP_API_KEY
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        local_results = results.get("local_results", [])
        for item in local_results:
            all_results.append({
                "title": item.get("title"),
                "address": item.get("address"),
                "phone": item.get("phone"),
                "website": item.get("website"),
            })

    return all_results
