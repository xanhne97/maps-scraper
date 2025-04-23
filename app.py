from flask import Flask, render_template, request, send_file
from scraper import scrape_from_keywords
import pandas as pd
import io

app = Flask(__name__)
last_data = []  # Dữ liệu tìm kiếm gần nhất (lưu tạm để xuất Excel)

@app.route("/", methods=["GET", "POST"])
def index():
    global last_data
    data = []
    if request.method == "POST":
        try:
            keyword_str = request.form.get("keywords", "")
            keywords = [kw.strip() for kw in keyword_str.splitlines() if kw.strip()]
            if keywords:
                data = scrape_from_keywords(keywords)
                last_data = data  # Lưu lại để dùng cho xuất Excel
        except Exception as e:
            print("❌ Lỗi tìm kiếm:", e)
    return render_template("index.html", data=data)

@app.route("/download", methods=["GET"])
def download_excel():
    global last_data
    if not last_data:
        return "Không có dữ liệu để xuất", 400

    df = pd.DataFrame(last_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="KetQua")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="ket_qua_google_maps.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(debug=True)
