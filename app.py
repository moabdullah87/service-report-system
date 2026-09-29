import os
import base64
import smtplib
from datetime import datetime
from email.message import EmailMessage
from PIL import Image, ImageOps
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from pdf_generator import generate_service_pdf
from pdi_generator import generate_pdi_pdf

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
REPORTS_FOLDER = os.path.join(os.getcwd(), "generated_reports")
COUNTER_FILE = os.path.join(os.getcwd(), "counter.txt")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# ========================================================
# إعدادات البريد الإلكتروني
# ========================================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SYSTEM_SENDER_EMAIL = "M7MD.3BDALH@GMAIL.COM"
SYSTEM_SENDER_PASSWORD = "ceizqoizqtokayeg"

TARGET_EMAILS = [
    "mohamed.abdullah@mcv-eg.com",
    "sara.elhadedy@mcv-eg.com"
]

def clean_text(text):
    if not text:
        return ""
    return str(text).replace("\xa0", "").replace(" ", "").strip()

def get_next_report_id():
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
    with open(COUNTER_FILE, "w") as f:
        f.write(str(current_count))
    return f"SR-{current_year}-{current_count:04d}"

def save_base64_sig(sig_data, prefix, report_id):
    if not sig_data or not sig_data.startswith("data:image"):
        return None
    try:
        format_info, img_str = sig_data.split(";base64,")
        sig_bytes = base64.b64decode(img_str)
        filename = f"{report_id}_{prefix}.png"
        path = os.path.join(UPLOAD_FOLDER, filename)
        with open(path, "wb") as f:
            f.write(sig_bytes)
        return path
    except Exception as e:
        print(f"[SIGNATURE ERROR] {e}")
        return None

def process_photo_batch(files_list, category_name, report_id):
    saved_paths = []
    for idx, file in enumerate(files_list):
        if file and file.filename.strip() != "":
            temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{category_name}_{idx}_{secure_filename(file.filename)}")
            file.save(temp_path)
            final_jpg_path = os.path.join(UPLOAD_FOLDER, f"{report_id}_{category_name}_{idx}.jpg")
            try:
                with Image.open(temp_path) as img:
                    img = ImageOps.exif_transpose(img)
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(final_jpg_path, "JPEG", quality=85)
                saved_paths.append(final_jpg_path)
            except Exception as e:
                print(f"[PHOTO ERROR] {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
    return saved_paths

def send_notification_email(subject, body, report_path, filename, cc_email=None):
    try:
        sender = clean_text(SYSTEM_SENDER_EMAIL).lower()
        password = clean_text(SYSTEM_SENDER_PASSWORD)
        recipients = [clean_text(e).lower() for e in TARGET_EMAILS]

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        
        if cc_email and "@" in cc_email:
            msg["Cc"] = clean_text(cc_email).lower()

        msg.set_content(body)

        with open(report_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=filename)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            print(f"[EMAIL SUCCESS] Sent to {', '.join(recipients)}")
            return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

# ========================================================
# Routes
# ========================================================

@app.route("/")
def home():
    """الصفحة الرئيسية لاختيار نوع النموذج"""
    return render_template("home.html")

@app.route("/service-report", methods=["GET", "POST"])
def service_report():
    if request.method == "POST":
        now = datetime.now()
        report_id = get_next_report_id()
        
        brand = request.form.get("brand", "generic").lower()
        brand_logos = {
            "jungheinrich": "static/logos/jungheinrich.png",
            "noblelift": "static/logos/noblelift.png",
            "nexen": "static/logos/nexen.png"
        }

        eng_sig_path = save_base64_sig(request.form.get("engineer_signature"), "eng_sig", report_id)
        client_sig_path = save_base64_sig(request.form.get("client_signature"), "client_sig", report_id)

        categorized_photos = {
            "before": process_photo_batch(request.files.getlist("photos_before"), "before", report_id),
            "defective": process_photo_batch(request.files.getlist("photos_defective"), "defective", report_id),
            "after": process_photo_batch(request.files.getlist("photos_after"), "after", report_id)
        }

        engineer_email = request.form.get("engineer_email", "").strip()

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
            "engineer_email": engineer_email,
            "client_rep": request.form.get("client_rep"),
            "engineer_sig_path": eng_sig_path,
            "client_sig_path": client_sig_path,
            "parts": []
        }

        part_nums = request.form.getlist("part_number[]")
        part_descs = request.form.getlist("part_desc[]")
        part_qtys = request.form.getlist("part_qty[]")
        part_statuses = request.form.getlist("part_status[]")

        for num, desc, qty, status in zip(part_nums, part_descs, part_qtys, part_statuses):
            if num.strip() or desc.strip():
                report_data["parts"].append({"number": num, "desc": desc, "qty": qty, "status": status})

        pdf_filename = f"{report_id}.pdf"
        output_pdf_path = os.path.join(REPORTS_FOLDER, pdf_filename)
        generate_service_pdf(report_data, output_pdf_path, photos_by_category=categorized_photos)

        # حذف الملفات المؤقتة
        temp_files = [eng_sig_path, client_sig_path]
        for cat_list in categorized_photos.values():
            temp_files.extend(cat_list)
        for p in temp_files:
            if p and os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

        # إرسال الإيميل
        email_body = f"""Dear Team,

A new Field Service Report has been generated:

- Serial: {report_id}
- Customer: {report_data['client_name']} ({report_data['site_location']})
- Equipment: {report_data['brand_display']} {report_data['model']} (S/N: {report_data['serial_number']})
- Operating Hours: {report_data['hours']} h
- Service Engineer: {report_data['engineer_name']} ({engineer_email})

Attached is the official report.
"""
        send_notification_email(f"Field Service Report: {report_data['brand_display']} [{report_id}]", email_body, output_pdf_path, pdf_filename, engineer_email)

        return send_file(output_pdf_path, as_attachment=False, mimetype="application/pdf")

    return render_template("index.html")

@app.route("/pdi", methods=["GET", "POST"])
def pdi():
    if request.method == "POST":
        serial_no = request.form.get("serial_no", "PDI-TRUCK")
        date_str = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        pdi_id = f"PDI-{serial_no}"
        sig_path = save_base64_sig(request.form.get("engineer_signature"), "pdi_sig", pdi_id)

        pdi_data = {
            "serial_no": serial_no,
            "date": date_str,
            "truck_type": request.form.get("truck_type"),
            "start_time": request.form.get("start_time"),
            "finish_time": request.form.get("finish_time"),
            "time_worked": request.form.get("time_worked"),
            "time_travelled": request.form.get("time_travelled"),
            "km_hours": request.form.get("km_hours"),
            "checked_items": request.form.getlist("pdi_check"),
            "sig_path": sig_path
        }

        pdf_filename = f"PDI_{serial_no}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"
        output_pdf_path = os.path.join(REPORTS_FOLDER, pdf_filename)
        generate_pdi_pdf(pdi_data, output_pdf_path)

        if sig_path and os.path.exists(sig_path):
            try: os.remove(sig_path)
            except Exception: pass

        email_body = f"""Dear Team,

A new Linde Pre-Delivery Inspection (PDI) has been completed and signed:

- Equipment Serial: {serial_no}
- Date: {date_str}
- Category: {pdi_data['truck_type']}
- Status: PASSED & COMMISSIONED

Please find the attached PDI certificate.
"""
        send_notification_email(f"Linde PDI Certificate: Truck S/N {serial_no}", email_body, output_pdf_path, pdf_filename)

        return send_file(output_pdf_path, as_attachment=False, mimetype="application/pdf")

    return render_template("pdi.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
