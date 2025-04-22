# app.py
from flask import Flask, render_template, request, send_file
from model import init_db, save_result, get_all_results
from scraper import scrape_mock_data
import pandas as pd
import os

app = Flask(__name__)
data = scrape_mock_data(keywords)
@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        keywords = request.form['keywords'].splitlines()
        for keyword in keywords:
            keyword = keyword.strip()
            if keyword:
                items = scrape_mock_data(keyword)
                results.extend(items)
                for r in items:
                    save_result(r['name'], r['address'], r['phone'])
        # Ghi tạm vào Excel để tải về sau
        df = pd.DataFrame(results)
        df.to_excel("output.xlsx", index=False)

    return render_template('index.html', results=results)


@app.route('/download')
def download():
    if os.path.exists("output.xlsx"):
        return send_file("output.xlsx", as_attachment=True)
    return "Không tìm thấy file. Hãy thực hiện tìm kiếm trước."

if __name__ == '__main__':
    init_db()
    app.run(debug=True)