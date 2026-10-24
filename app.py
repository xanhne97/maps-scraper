from flask import Flask, render_template, request, send_file, abort
from scraper import scrape_from_keywords, SCAN_LEVELS
import pandas as pd
import io
import json
import os
import re
import sys
import tempfile
import time
import uuid

# Console Windows mặc định cp1252, in emoji/tiếng Việt ra log sẽ lỗi làm hỏng cả request
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

app = Flask(__name__)

# Kết quả mỗi lượt tìm lưu ra file riêng theo search_id, để nhiều người dùng
# (và nhiều worker gunicorn) không ghi đè dữ liệu của nhau
RESULTS_DIR = os.path.join(tempfile.gettempdir(), "maps_scraper")
RESULTS_TTL = 24 * 3600
os.makedirs(RESULTS_DIR, exist_ok=True)

EXCEL_COLUMNS = {
    "title": "Tên",
    "category": "Loại hình",
    "address": "Địa chỉ",
    "phone": "Điện thoại",
    "website": "Website",
    "rating": "Đánh giá",
    "reviews": "Số lượt đánh giá",
    "distance": "Khoảng cách (m)",
    "lat": "Vĩ độ",
    "lng": "Kinh độ",
    "maps_url": "Google Maps",
    "keywords": "Từ khóa",
}


def _result_path(search_id):
    if not re.fullmatch(r"[0-9a-f]{32}", search_id):
        abort(404)
    return os.path.join(RESULTS_DIR, f"{search_id}.json")


def _save_results(results):
    now = time.time()
    for name in os.listdir(RESULTS_DIR):
        path = os.path.join(RESULTS_DIR, name)
        if now - os.path.getmtime(path) > RESULTS_TTL:
            os.remove(path)

    search_id = uuid.uuid4().hex
    with open(_result_path(search_id), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    return search_id


def _parse_coords(form):
    """Nhận tọa độ từ 2 ô, hoặc dán nguyên chuỗi "10.95, 106.81" từ Google Maps vào ô vĩ độ."""
    lat_str = form.get("latitude", "").strip()
    lng_str = form.get("longitude", "").strip()
    if "," in lat_str and not lng_str:
        lat_str, lng_str = (s.strip() for s in lat_str.split(",", 1))
    try:
        lat, lng = float(lat_str), float(lng_str)
    except ValueError:
        raise ValueError("Tọa độ không hợp lệ, hãy nhập vĩ độ và kinh độ dạng số")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("Tọa độ nằm ngoài phạm vi cho phép")
    return lat, lng


@app.route("/", methods=["GET", "POST"])
def index():
    context = {"data": [], "levels": SCAN_LEVELS}
    if request.method == "POST":
        try:
            keywords = list(dict.fromkeys(
                kw.strip() for kw in request.form.get("keywords", "").splitlines() if kw.strip()
            ))
            if not keywords:
                raise ValueError("Hãy nhập ít nhất một từ khóa")
            center_coords = _parse_coords(request.form)
            radius_m = request.form.get("radius_m", type=int)
            level = request.form.get("level", "normal")

            outcome = scrape_from_keywords(keywords, center_coords=center_coords, radius_m=radius_m, level=level)
            context.update(
                data=outcome["results"],
                stats=outcome["stats"],
                warnings=outcome["errors"],
                search_id=_save_results(outcome["results"]) if outcome["results"] else None,
            )
        except Exception as e:
            print("❌ Lỗi tìm kiếm:", e)
            context["error"] = str(e)
    return render_template("index.html", **context)


@app.route("/download/<search_id>", methods=["GET"])
def download_excel(search_id):
    path = _result_path(search_id)
    if not os.path.exists(path):
        return "Kết quả đã hết hạn, hãy tìm kiếm lại", 404

    try:
        with open(path, encoding="utf-8") as f:
            df = pd.DataFrame(json.load(f))
        df = df[[c for c in EXCEL_COLUMNS if c in df.columns]].rename(columns=EXCEL_COLUMNS)
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
