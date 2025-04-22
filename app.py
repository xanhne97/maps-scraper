# app.py
from flask import Flask, render_template, request
from app.models import init_db, save_result, get_all_results
from scraper import scrape_mock_data

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        keyword = request.form['keyword']
        results = scrape_mock_data(keyword)
        for r in results:
            save_result(r['name'], r['address'], r['phone'])
    history = get_all_results()
    return render_template('index.html', results=results, history=history)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
