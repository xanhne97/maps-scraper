import os
from serpapi.google_search_results import GoogleSearch

SERP_API_KEY = os.getenv("SERPAPI_API_KEY")  # Bạn phải set biến môi trường này trên Render

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
