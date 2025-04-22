# scraper.py
def scrape_mock_data(keyword):
    # Tạm thời dùng dữ liệu giả để test trước khi dùng selenium thật
    return [
        {"name": f"{keyword} Garage A", "address": "123 Đường A, Quận 1", "phone": "0909000001"},
        {"name": f"{keyword} Auto B",   "address": "456 Đường B, Quận 1", "phone": "0909000002"},
        {"name": f"{keyword} Repair C", "address": "789 Đường C, Quận 1", "phone": "0909000003"}
    ]
