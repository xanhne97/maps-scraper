from flask import Flask, render_template, request
from scraper import scrape_from_keywords

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    data = []
    if request.method == "POST":
        keyword_str = request.form.get("keywords", "")
        keywords = [kw.strip() for kw in keyword_str.splitlines() if kw.strip()]
        if keywords:
            data = scrape_from_keywords(keywords)
    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)
