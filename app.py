import os
import base64
import smtplib
from datetime import datetime
from email.message import EmailMessage
from PIL import Image, ImageOps
from fpdf import FPDF
from flask import Flask, render_template, render_template_string, request, send_file
from werkzeug.utils import secure_filename
from pdf_generator import generate_service_pdf

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
REPORTS_FOLDER = os.path.join(os.getcwd(), "generated_reports")
COUNTER_FILE = os.path.join(os.getcwd(), "counter.txt")
PDI_COUNTER_FILE = os.path.join(os.getcwd(), "pdi_counter.txt")

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

def safe_pdf_str(text):
    """تأمين النصوص المدخلة لمنع أي خطأ ترميز في FPDF"""
    if not text:
        return "-"
    try:
        return str(text).encode("latin-1").decode("latin-1")
    except UnicodeEncodeError:
        return str(text).encode("ascii", "replace").decode("ascii")

def get_next_report_id():
    """توليد رقم تسلسلي لتقارير الصيانة SR-YYYY-XXXX"""
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

def get_next_pdi_id():
    """توليد رقم تسلسلي لتقارير الفحص PDI-YYYY-XXXX"""
    current_year = datetime.now().strftime("%Y")
    current_count = 1
    if os.path.exists(PDI_COUNTER_FILE):
        try:
            with open(PDI_COUNTER_FILE, "r") as f:
                content = f.read().strip()
                if content.isdigit():
                    current_count = int(content) + 1
        except Exception:
            current_count = 1
    with open(PDI_COUNTER_FILE, "w") as f:
        f.write(str(current_count))
    return f"PDI-{current_year}-{current_count:04d}"

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

def process_single_photo(file_storage, tag, report_id):
    if not file_storage or file_storage.filename.strip() == "":
        return None
    temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{tag}_{secure_filename(file_storage.filename)}")
    file_storage.save(temp_path)
    final_jpg_path = os.path.join(UPLOAD_FOLDER, f"{report_id}_{tag}.jpg")
    try:
        with Image.open(temp_path) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(final_jpg_path, "JPEG", quality=85)
        return final_jpg_path
    except Exception as e:
        print(f"[PHOTO ERROR] {tag}: {e}")
        return None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

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
# محرك PDI المحدث (مع قسم الملاحظات والترقيم واللوجوهات)
# ========================================================
class PDIPDF(FPDF):
    def __init__(self, brand_logo=None, mcv_logo=None, report_id=None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.brand_logo = brand_logo
        self.mcv_logo = mcv_logo
        self.report_id = report_id or "PDI-REPORT"

    def header(self):
        self.set_fill_color(248, 250, 252)
        self.rect(10, 8, 190, 24, "F")
        
        # MCV Logo on Left
        if self.mcv_logo and os.path.exists(self.mcv_logo):
            try:
                self.image(self.mcv_logo, x=13, y=12, w=35)
            except Exception:
                pass
        
        # Centered Text Titles + Report Number
        self.set_xy(50, 9.5)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(15, 23, 42)
        self.cell(100, 5, "PRE-DELIVERY INSPECTION (PDI)", 0, 1, "C")
        
        self.set_x(50)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(100, 116, 139)
        self.cell(100, 4, "Commissioning & Final Quality Sign-Off Certificate", 0, 1, "C")
        
        self.set_x(50)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(220, 38, 38)
        self.cell(100, 4, f"Report No: {self.report_id}", 0, 0, "C")
        
        # Brand Logo on Right
        if self.brand_logo and os.path.exists(self.brand_logo):
            try:
                self.image(self.brand_logo, x=155, y=13, w=38)
            except Exception:
                pass

        self.set_y(34)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 6, f"Page {self.page_no()}/{{nb}} - Official Pre-Delivery Record [{self.report_id}]", align="C")

def pdi_bar(pdf, title):
    pdf.ln(2)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(190, 5.5, f"  {title}", fill=True, border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)

def generate_pdi_pdf(data, output_path):
    pdf = PDIPDF(
        brand_logo=data.get("brand_logo"),
        mcv_logo=data.get("mcv_logo"),
        report_id=data.get("report_id")
    )
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # 1. Equipment Details
    pdi_bar(pdf, "1. EQUIPMENT & INSPECTION RECORD")
    w_lbl, w_val = 35, 60
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(71, 85, 105)
    
    # Row 1 (Report ID & Brand)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(w_lbl, 6, "PDI Report ID:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(220, 38, 38)
    pdf.cell(w_val, 6, safe_pdf_str(data.get("report_id", "-")), 1, 0, "L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Equipment Brand:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, safe_pdf_str(data.get("brand_display", "-")), 1, 1, "L")

    # Row 2 (Serial & Date)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(w_lbl, 6, "Truck Serial No:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, safe_pdf_str(data.get("serial_no", "-")), 1, 0, "L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Inspection Date:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, safe_pdf_str(data.get("date", "-")), 1, 1, "L")

    # Row 3 (Category & Hours)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Truck Category:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, safe_pdf_str(data.get("truck_type", "-")), 1, 0, "L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Operating KM / Hours:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, safe_pdf_str(data.get("km_hours", "-")), 1, 1, "L")

    # Row 4 (Time & Travel)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Inspection Time:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, safe_pdf_str(f"{data.get('start_time','-')} to {data.get('finish_time','-')}"), 1, 0, "L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Worked / Travelled:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, safe_pdf_str(f"{data.get('time_worked','-')} / {data.get('time_travelled','-')}"), 1, 1, "L")
    pdf.ln(2)

    # 2. Checklist Verification (PASS vs N/A)
    pdi_bar(pdf, "2. COMPLETED QUALITY VERIFICATION CHECKLIST")
    checked_items = data.get("checked_items", [])
    col_w = 93
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(30, 41, 59)

    if checked_items:
        for i in range(0, len(checked_items), 2):
            item1 = checked_items[i]
            t1 = safe_pdf_str(item1.get("title", ""))
            s1 = item1.get("status", "PASS")
            tag1 = f"[{s1:^5}]"
            pdf.cell(col_w, 5.5, f"  {tag1}  {t1}", border=1)
            pdf.cell(4, 5.5, "", 0, 0)
            
            if i + 1 < len(checked_items):
                item2 = checked_items[i+1]
                t2 = safe_pdf_str(item2.get("title", ""))
                s2 = item2.get("status", "PASS")
                tag2 = f"[{s2:^5}]"
                pdf.cell(col_w, 5.5, f"  {tag2}  {t2}", border=1, new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.ln(5.5)
    else:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(190, 6, "Checklist verification completed.", border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)

    # 3. General Remarks Section
    pdi_bar(pdf, "3. GENERAL REMARKS & OBSERVATIONS")
    remarks = data.get("remarks", "").strip()
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    
    if remarks:
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.multi_cell(190, 5, f"  {safe_pdf_str(remarks)}", border=1, fill=True)
    else:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(190, 6, "  No specific remarks or observations recorded.", border=1, fill=True, align="L", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)

    # 4. Multiple Inspectors Sign-off
    pdi_bar(pdf, "4. COMMISSIONING INSPECTION TEAM & SIGN-OFF")
    inspectors = data.get("inspectors", [])
    card_w = 93
    card_h = 28
    
    for idx, insp in enumerate(inspectors):
        col = idx % 2
        if col == 0 and idx > 0:
            pdf.ln(card_h + 3)
            
        cur_y = pdf.get_y()
        cur_x = 10 if col == 0 else 107

        pdf.set_xy(cur_x, cur_y)
        pdf.set_draw_color(203, 213, 225)
        pdf.rect(cur_x, cur_y, card_w, card_h)

        pdf.set_xy(cur_x + 3, cur_y + 2)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(card_w - 6, 4, f"INSPECTOR #{idx + 1}:", 0, 1, "L")

        pdf.set_x(cur_x + 3)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(card_w - 6, 4, safe_pdf_str(insp.get("name", "Service Engineer")), 0, 1, "L")

        sig_path = insp.get("sig_path")
        if sig_path and os.path.exists(sig_path):
            try:
                pdf.image(sig_path, x=cur_x + 20, y=cur_y + 9, w=50, h=17)
            except Exception:
                pass

    if inspectors:
        pdf.set_y(pdf.get_y() + card_h + 3)

    # Status Bar
    status_y = pdf.get_y()
    pdf.set_fill_color(240, 253, 244)
    pdf.set_draw_color(187, 247, 208)
    pdf.rect(10, status_y, 190, 8.5, "DF")
    pdf.set_xy(12, status_y + 1.8)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(186, 5, "FINAL STATUS: QUALIFIED & APPROVED FOR CUSTOMER HANDOVER", 0, 0, "C")

    # ========================================================
    # Page 2: Four-Side Photographic Record (2x2 Grid)
    # ========================================================
    side_photos = data.get("side_photos", {})
    has_any_side_photo = any(side_photos.values())

    if has_any_side_photo:
        pdf.add_page()
        pdi_bar(pdf, "5. EQUIPMENT 360-DEGREE PHOTOGRAPHIC RECORD")
        pdf.ln(1)

        photo_slots = [
            ("1. FRONT VIEW", side_photos.get("front")),
            ("2. REAR VIEW", side_photos.get("rear")),
            ("3. LEFT SIDE VIEW", side_photos.get("left")),
            ("4. RIGHT SIDE VIEW", side_photos.get("right")),
        ]

        grid_w = 92
        grid_h = 95
        grid_margin_x = 10
        gap_x = 6
        gap_y = 6
        start_y = pdf.get_y()

        for idx, (label, img_path) in enumerate(photo_slots):
            row = idx // 2
            col = idx % 2

            pos_x = grid_margin_x + col * (grid_w + gap_x)
            pos_y = start_y + row * (grid_h + gap_y)

            pdf.set_draw_color(203, 213, 225)
            pdf.set_fill_color(248, 250, 252)
            pdf.rect(pos_x, pos_y, grid_w, grid_h, "DF")

            pdf.set_xy(pos_x, pos_y + 1)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(grid_w, 6, label, 0, 1, "C")

            if img_path and os.path.exists(img_path):
                try:
                    pdf.image(img_path, x=pos_x + 3, y=pos_y + 8, w=grid_w - 6, h=grid_h - 11)
                except Exception as e:
                    print(f"[PDF IMG ERROR] {e}")
            else:
                pdf.set_xy(pos_x, pos_y + 40)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(148, 163, 184)
                pdf.cell(grid_w, 6, "No Photo Uploaded", 0, 0, "C")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pdf.output(output_path)
    return output_path

# ========================================================
# واجهة الصفحة الرئيسية المدمجة
# ========================================================
HOME_HTML_FALLBACK = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بوابة الخدمات الفنية | Service Portal</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #f8fafc; margin: 0; padding: 20px; display: flex; align-items: center; justify-content: center; min-height: 95vh; }
        .container { width: 100%; max-width: 440px; text-align: center; }
        .logo-title { font-size: 26px; font-weight: 800; color: #dc2626; margin-bottom: 4px; }
        .portal-title { font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }
        .portal-sub { font-size: 13px; color: #64748b; margin-bottom: 25px; }
        .cards { display: flex; flex-direction: column; gap: 15px; }
        .card-btn {
            display: flex; align-items: center; background: #ffffff; border: 2px solid #e2e8f0;
            border-radius: 12px; padding: 18px; text-decoration: none; color: #1e293b;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04); transition: all 0.2s ease;
        }
        .card-btn:hover { border-color: #0284c7; transform: translateY(-2px); }
        .icon { width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; margin-left: 14px; flex-shrink: 0; }
        .icon-service { background: #fee2e2; color: #dc2626; }
        .icon-pdi { background: #e0f2fe; color: #0284c7; }
        .text { text-align: right; flex-grow: 1; }
        .text h3 { margin: 0 0 4px 0; font-size: 16px; color: #0f172a; }
        .text p { margin: 0; font-size: 12px; color: #64748b; }
        .arrow { font-size: 18px; color: #cbd5e1; transform: scaleX(-1); }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-title">MCV</div>
        <div class="portal-title">Field Service Portal</div>
        <div class="portal-sub">اختر نوع النموذج المطلوب للبدء:</div>
        <div class="cards">
            <a href="/service-report" class="card-btn">
                <div class="icon icon-service">🛠</div>
                <div class="text">
                    <h3>Service Report</h3>
                    <p>تقرير صيانة وإصلاح أعطال المعدات الميدانية</p>
                </div>
                <div class="arrow">➜</div>
            </a>
            <a href="/pdi" class="card-btn">
                <div class="icon icon-pdi">📋</div>
                <div class="text">
                    <h3>PDI Form</h3>
                    <p>فحص وتشغيل ما قبل التسليم (Pre-Delivery)</p>
                </div>
                <div class="arrow">➜</div>
            </a>
        </div>
    </div>
</body>
</html>
"""

# ========================================================
# Routes
# ========================================================

@app.route("/")
def home():
    try:
        return render_template("home.html")
    except Exception:
        return render_template_string(HOME_HTML_FALLBACK)

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

        temp_files = [eng_sig_path, client_sig_path]
        for cat_list in categorized_photos.values():
            temp_files.extend(cat_list)
        for p in temp_files:
            if p and os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

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
        pdi_report_id = get_next_pdi_id()
        serial_no = request.form.get("serial_no", "PDI-TRUCK")
        date_str = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
        brand = request.form.get("brand", "jungheinrich").lower()
        remarks = request.form.get("remarks", "").strip()

        brand_logos = {
            "jungheinrich": "static/logos/jungheinrich.png",
            "noblelift": "static/logos/noblelift.png",
            "nexen": "static/logos/nexen.png"
        }

        # 1. فريق الفحص والتوقيعات
        inspector_names = request.form.getlist("inspector_name[]")
        inspector_sigs = request.form.getlist("inspector_sig[]")
        inspectors_list = []
        temp_files_to_clean = []

        for idx, (name, sig_data) in enumerate(zip(inspector_names, inspector_sigs)):
            if name.strip():
                sig_path = save_base64_sig(sig_data, f"inspector_{idx}", pdi_report_id)
                if sig_path:
                    temp_files_to_clean.append(sig_path)
                inspectors_list.append({"name": name.strip(), "sig_path": sig_path})

        # 2. استخراج بنود الفحص الإجبارية (PASS vs N/A)
        checklist_items = []
        idx = 0
        while f"check_title_{idx}" in request.form:
            title = request.form.get(f"check_title_{idx}")
            status = request.form.get(f"check_status_{idx}")
            if title and status:
                checklist_items.append({"title": title, "status": status})
            idx += 1

        # 3. صور الجوانب الأربعة
        side_photos = {
            "front": process_single_photo(request.files.get("photo_front"), "front", pdi_report_id),
            "rear": process_single_photo(request.files.get("photo_rear"), "rear", pdi_report_id),
            "left": process_single_photo(request.files.get("photo_left"), "left", pdi_report_id),
            "right": process_single_photo(request.files.get("photo_right"), "right", pdi_report_id)
        }
        for sp in side_photos.values():
            if sp:
                temp_files_to_clean.append(sp)

        pdi_data = {
            "report_id": pdi_report_id,
            "brand": brand,
            "brand_display": brand.upper(),
            "brand_logo": brand_logos.get(brand),
            "mcv_logo": "static/logos/mcv.png",
            "serial_no": serial_no,
            "date": date_str,
            "truck_type": request.form.get("truck_type"),
            "start_time": request.form.get("start_time"),
            "finish_time": request.form.get("finish_time"),
            "time_worked": request.form.get("time_worked"),
            "time_travelled": request.form.get("time_travelled"),
            "km_hours": request.form.get("km_hours"),
            "checked_items": checklist_items,
            "remarks": remarks,
            "inspectors": inspectors_list,
            "side_photos": side_photos
        }

        # تسمية الملف برقم التقرير والمعدة
        pdf_filename = f"{pdi_report_id}_{brand.upper()}_{serial_no}.pdf"
        output_pdf_path = os.path.join(REPORTS_FOLDER, pdf_filename)
        generate_pdi_pdf(pdi_data, output_pdf_path)

        for p in temp_files_to_clean:
            if p and os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

        names_str = ", ".join([insp['name'] for insp in inspectors_list])
        remarks_line = f"\n- Remarks: {remarks}" if remarks else ""
        email_body = f"""Dear Team,

A new Pre-Delivery Inspection (PDI) has been completed and signed:

- Report ID: {pdi_report_id}
- Brand: {pdi_data['brand_display']}
- Equipment Serial: {serial_no}
- Date: {date_str}
- Inspection Team: {names_str}{remarks_line}
- Status: PASSED & COMMISSIONED

Attached is the official PDI certificate with complete 360-degree inspection photos.
"""
        send_notification_email(f"PDI Certificate: {pdi_data['brand_display']} [{pdi_report_id}] (S/N: {serial_no})", email_body, output_pdf_path, pdf_filename)

        return send_file(output_pdf_path, as_attachment=False, mimetype="application/pdf")

    return render_template("pdi.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
