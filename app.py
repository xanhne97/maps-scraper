from flask import Flask, render_template, request
from scraper import scrape_mock_data  # hoặc scrape_real_data nếu bạn dùng requests

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    data = []
    if request.method == "POST":
        keywords = request.form.get("keywords")
        if keywords:
            data = scrape_mock_data(keywords)  # hoặc scrape_real_data(keywords)

    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)
