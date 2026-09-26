import os
from datetime import datetime
from flask import Flask, render_template, request, send_file, redirect, url_for
from werkzeug.utils import secure_filename
from pdf_generator import generate_service_pdf

app = Flask(__name__)

# Base folder configurations
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
REPORTS_FOLDER = os.path.join(os.getcwd(), "generated_reports")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Generate automatic serial number: SR-YYYYMMDD-HHMM
        now = datetime.now()
        report_id = f"SR-{now.strftime('%Y%m%d-%H%M')}"
        
        # Collect client and machine details from form
        report_data = {
            "report_id": report_id,
            "date": request.form.get("date") or now.strftime("%Y-%m-%d"),
            "client_name": request.form.get("client_name"),
            "site_location": request.form.get("site_location"),
            "contact_person": request.form.get("contact_person"),
            "contact_phone": request.form.get("contact_phone"),
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

        # Collect up to 4 spare parts rows
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

        # Process uploaded site images
        uploaded_images = []
        files = request.files.getlist("photos")
        for file in files[:4]:
            if file and allowed_file(file.filename):
                fname = secure_filename(f"{report_id}_{file.filename}")
                save_path = os.path.join(UPLOAD_FOLDER, fname)
                file.save(save_path)
                uploaded_images.append(save_path)

        # Generate the PDF file
        pdf_filename = f"{report_id}.pdf"
        output_pdf_path = os.path.join(REPORTS_FOLDER, pdf_filename)
        generate_service_pdf(report_data, output_pdf_path, photos=uploaded_images)

        # Send the created PDF directly for viewing/download
        return send_file(output_pdf_path, as_attachment=True, download_name=pdf_filename)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
