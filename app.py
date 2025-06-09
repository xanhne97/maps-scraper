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
            lat = request.form.get("latitude", type=float)
            lng = request.form.get("longitude", type=float)
            radius_m = request.form.get("radius_m", type=int)

            if not lat or not lng:
                raise ValueError("Thiếu tọa độ")

            keywords = [kw.strip() for kw in keyword_str.splitlines() if kw.strip()]
            if keywords:
                center_coords = (lat, lng)
                data = scrape_from_keywords(keywords, center_coords=center_coords, radius_m=radius_m)
                last_data = data
        except Exception as e:
            print("❌ Lỗi tìm kiếm:", e)
    return render_template("index.html", data=data)

@app.route("/download", methods=["GET"])
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

        return send_file(
            output,
            as_attachment=True,
            download_name="ket_qua_google_maps.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        print("❌ Lỗi khi xuất Excel:", e)
        return f"Lỗi khi xuất Excel: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)
