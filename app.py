import os
from datetime import datetime
from PIL import Image, ImageOps
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from pdf_generator import generate_service_pdf

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
REPORTS_FOLDER = os.path.join(os.getcwd(), "generated_reports")
COUNTER_FILE = os.path.join(os.getcwd(), "counter.txt")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

def get_next_report_id():
    """توليد رقم تسلسلي منتظم وحفظه تلقائياً"""
    current_year = datetime.now().strftime("%Y")
    current_count = 1

    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                content = f.read().strip()
                if content.isdigit():
                    current_count = int(content) + 1
        except Exception:
            current_count = 1

    # حفظ الرقم الجديد
    with open(COUNTER_FILE, "w") as f:
        f.write(str(current_count))

    # التنسيق: SR-2026-0001 (أربعة خانات قابلة للزيادة)
    return f"SR-{current_year}-{current_count:04d}"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        now = datetime.now()
        report_id = get_next_report_id()
        
        brand = request.form.get("brand", "generic").lower()
        brand_logos = {
            "jungheinrich": "static/logos/jungheinrich.png",
            "noblelift": "static/logos/noblelift.png",
            "nexen": "static/logos/nexen.png"
        }

        report_data = {
            "report_id": report_id,
            "date": request.form.get("date") or now.strftime("%Y-%m-%d"),
            "mcv_logo": "static/logos/mcv.png",
            "brand_logo": brand_logos.get(brand),
            "client_name": request.form.get("client_name"),
            "site_location": request.form.get("site_location"),
            "contact_person": request.form.get("contact_person"),
            "contact_phone": request.form.get("contact_phone"),
            "brand_display": brand.upper(),
            "model": request.form.get("model"),
            "serial_number": request.form.get("serial_number"),
            "hours": request.form.get("hours"),
            "service_type": request.form.get("service_type"),
            "reported_issue": request.form.get("reported_issue"),
            "actions_taken": request.form.get("actions_taken"),
            "engineer_name": request.form.get("engineer_name"),
            "client_rep": request.form.get("client_rep"),
            "parts": []
        }

        # Parts
        part_nums = request.form.getlist("part_number[]")
        part_descs = request.form.getlist("part_desc[]")
        part_qtys = request.form.getlist("part_qty[]")
        part_statuses = request.form.getlist("part_status[]")

        for num, desc, qty, status in zip(part_nums, part_descs, part_qtys, part_statuses):
            if num.strip() or desc.strip():
                report_data["parts"].append({
                    "number": num,
                    "desc": desc,
                    "qty": qty,
                    "status": status
                })

        # Save and auto-orient photos
        uploaded_images = []
        files = request.files.getlist("photos")

        for idx, file in enumerate(files):
            if file and file.filename.strip() != "":
                temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{idx}_{secure_filename(file.filename)}")
                file.save(temp_path)
                
                final_jpg_path = os.path.join(UPLOAD_FOLDER, f"{report_id}_img_{idx}.jpg")
                try:
                    with Image.open(temp_path) as img:
                        img = ImageOps.exif_transpose(img)
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        img.save(final_jpg_path, "JPEG", quality=85)
                    uploaded_images.append(final_jpg_path)
                except Exception as e:
                    print(f"[ERROR] Could not process {file.filename}: {e}")
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

        # Generate PDF
        pdf_filename = f"{report_id}.pdf"
        output_pdf_path = os.path.join(REPORTS_FOLDER, pdf_filename)
        generate_service_pdf(report_data, output_pdf_path, photos=uploaded_images)

        return send_file(output_pdf_path, as_attachment=False, mimetype="application/pdf")

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)