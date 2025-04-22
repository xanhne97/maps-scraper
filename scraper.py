import requests
from bs4 import BeautifulSoup
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def search_google_maps(keyword):
    results = []

    query = f'site:google.com/maps {keyword}'
    url = f'https://www.google.com/search?q={requests.utils.quote(query)}'

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    for g in soup.select('div.g'):
        title = g.select_one('h3')
        link = g.find('a', href=True)
        snippet = g.select_one('.VwiC3b')

        name = title.text if title else ''
        address = ''
        phone = ''
        website = ''
        email = ''

        if snippet:
            text = snippet.text
            # Tìm địa chỉ
            if 'Địa chỉ' in text:
                match = re.search(r'Địa chỉ[:：]?\s*(.+?)(\s{2,}|$)', text)
                if match:
                    address = match.group(1).strip()

            # Tìm số điện thoại
            phone_match = re.search(r'(\+84[\d\s]+|0\d{9,10})', text)
            if phone_match:
                phone = phone_match.group(1)

            # Tìm website
            web_match = re.search(r'(https?://[^\s]+)', text)
            if web_match:
                website = web_match.group(1)

            # Tìm email
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
            if email_match:
                email = email_match.group(0)

        results.append({
            'name': name,
            'address': address,
            'phone': phone,
            'website': website,
            'email': email,
            'link': link['href'] if link else '',
        })

    return results


def scrape_mock_data(keywords):
    all_results = []
    for kw in keywords:
        all_results.extend(search_google_maps(kw))
    return all_results
