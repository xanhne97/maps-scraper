from flask import Flask, render_template, request, send_file
from scraper import scrape_from_keywords
import pandas as pd
import io

app = Flask(__name__)
last_data = []

@app.route("/", methods=["GET", "POST"])
def index():
    global last_data
    data = []
    if request.method == "POST":
        try:
            keyword_str = request.form.get("keywords", "")
            lat = float(request.form.get("latitude", 0))
            lng = float(request.form.get("longitude", 0))
            radius_km = float(request.form.get("radius_km", 0))
            radius_m = radius_km * 1000 if radius_km else None

            keywords = [kw.strip() for kw in keyword_str.splitlines() if kw.strip()]
            if keywords:
                data = scrape_from_keywords(keywords, center_coords=(lat, lng), radius_m=radius_m)
                last_data = data
        except Exception as e:
            print("❌ Lỗi tìm kiếm:", e)

    return render_template("index.html", data=data)

@app.route("/download")
def download_excel():
    global last_data
    if not last_data:
        return "Không có dữ liệu để xuất", 400

    try:
        df = pd.DataFrame(last_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="KetQua")
        output.seek(0)

        return send_file(output, as_attachment=True, download_name="ket_qua_google_maps.xlsx")
    except Exception as e:
        return f"Lỗi xuất Excel: {str(e)}", 500
