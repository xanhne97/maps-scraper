def scrape_from_keywords(keywords):
    results = []
    for keyword in keywords:
        # Thay phần này bằng scraper thật hoặc mock
        results.append({
            "name": f"Kết quả cho {keyword}",
            "address": "123 Đường A, Q.B, TP.HCM",
            "phone": "0123 456 789",
            "email": "email@example.com",
            "website": "https://example.com"
        })
    return results
