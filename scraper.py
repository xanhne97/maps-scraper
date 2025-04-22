# scraper.py
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else ""

def scrape_mock_data(keyword):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,800")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    results = []
    try:
        driver.get("https://www.google.com/maps")
        time.sleep(2)

        search_box = driver.find_element(By.ID, "searchboxinput")
        search_box.send_keys(keyword)
        driver.find_element(By.ID, "searchbox-searchbutton").click()
        time.sleep(5)

        for _ in range(3):
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            time.sleep(1)

        items = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
        for i, item in enumerate(items[:5]):  # Lấy 5 kết quả đầu tiên
            try:
                item.click()
                time.sleep(3)

                name = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf").text

                # Mặc định
                address = phone = email = website = ""

                # Tìm theo nhóm span chứa info
                spans = driver.find_elements(By.CSS_SELECTOR, "div.Io6YTe span")
                for span in spans:
                    text = span.text
                    if "Địa chỉ" in text or "P." in text or "Q." in text:
                        address = text
                    elif text.startswith("0") or text.startswith("+84"):
                        phone = text
                    elif "@" in text:
                        email = extract_email(text)

                # Tìm website
                links = driver.find_elements(By.CSS_SELECTOR, "a")
                for link in links:
                    href = link.get_attribute("href")
                    if href and "http" in href and not "google.com" in href:
                        website = href
                        break

                results.append({
                    "name": name,
                    "address": address,
                    "phone": phone,
                    "email": email,
                    "website": website
                })

                driver.back()
                time.sleep(2)
                items = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
            except Exception as e:
                print(f"❌ Lỗi tại mục {i + 1}: {e}")
                continue

    finally:
        driver.quit()

    return results
