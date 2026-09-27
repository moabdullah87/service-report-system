import os
from datetime import datetime
from PIL import Image
from fpdf import FPDF

class ServiceReportPDF(FPDF):
    def __init__(self, mcv_logo=None, brand_logo=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mcv_logo = mcv_logo
        self.brand_logo = brand_logo

    def header(self):
        # 1. Left Logo (MCV) - تم تكبيره لارتفاع 18 مم
        if self.mcv_logo and os.path.exists(self.mcv_logo):
            try:
                self.image(self.mcv_logo, x=10, y=6, w=36, h=18, keep_aspect_ratio=True)
            except Exception:
                pass

        # 2. Right Logo (Brand) - تم تكبيره لارتفاع 18 مم
        if self.brand_logo and os.path.exists(self.brand_logo):
            try:
                self.image(self.brand_logo, x=154, y=6, w=38, h=18, keep_aspect_ratio=True)
            except Exception:
                pass

        # 3. Center Header Title
        self.set_y(8)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 41, 59)
        self.cell(0, 6, "FIELD SERVICE REPORT", border=0, new_x="LMARGIN", new_y="NEXT", align="C")
        
        self.set_font("Helvetica", "", 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 4, "Technical Maintenance & Equipment Inspection", border=0, new_x="LMARGIN", new_y="NEXT", align="C")
        
        # مسافة للخط الفاصل ليتناسب مع الحجم الجديد للشعارات
        self.set_y(26)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}} - Confidential Technical Service Record", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(241, 245, 249)
        self.set_text_color(15, 23, 42)
        self.cell(0, 6, f"  {title}", border=0, new_x="LMARGIN", new_y="NEXT", align="L", fill=True)
        self.ln(2)

    def info_row(self, c1_title, c1_val, c2_title, c2_val, c1_w=32, c2_w=44):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(71, 85, 105)
        self.cell(c1_w, 5, c1_title, border=0)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(15, 23, 42)
        self.cell(95 - c1_w, 5, str(c1_val or "-"), border=0)

        self.set_font("Helvetica", "B", 8)
        self.set_text_color(71, 85, 105)
        self.cell(c2_w, 5, c2_title, border=0)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(15, 23, 42)
        self.cell(95 - c2_w, 5, str(c2_val or "-"), border=0, new_x="LMARGIN", new_y="NEXT")


def generate_service_pdf(data, output_path, photos=None):
    pdf = ServiceReportPDF(
        mcv_logo=data.get("mcv_logo"),
        brand_logo=data.get("brand_logo"),
        orientation="P", 
        unit="mm", 
        format="A4"
    )
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Meta Info
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(95, 5, f"Report ID: {data.get('report_id', 'SR-PENDING')}", border=0)
    pdf.cell(95, 5, f"Date: {data.get('date', datetime.today().strftime('%Y-%m-%d'))}", border=0, new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(2)

    # 1. Client Details
    pdf.section_title("1. CLIENT & SITE DETAILS")
    pdf.info_row("Client Name:", data.get("client_name"), "Site / Branch:", data.get("site_location"))
    pdf.info_row("Contact Person:", data.get("contact_person"), "Contact Phone:", data.get("contact_phone"))
    pdf.ln(2)

    # 2. Machine Specifications
    pdf.section_title("2. MACHINE SPECIFICATIONS")
    pdf.info_row("Brand & Model:", f"{data.get('brand_display')} {data.get('model')}", "Serial Number:", data.get("serial_number"))
    pdf.info_row("Operating Hours:", data.get("hours"), "Service Type:", data.get("service_type"))
    pdf.ln(2)

    # 3. Defect Description
    pdf.section_title("3. ISSUE DESCRIPTION & ROOT CAUSE")
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4.5, data.get("reported_issue", "-"))
    pdf.ln(2)

    # 4. Actions Taken
    pdf.section_title("4. ACTIONS TAKEN & REMARKS")
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4.5, data.get("actions_taken", "-"))
    pdf.ln(2)

    # 5. Spare Parts Table
    parts = data.get("parts", [])
    if parts:
        pdf.section_title("5. REPLACED / REQUIRED SPARE PARTS")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(226, 232, 240)
        pdf.cell(35, 6, "Part Number", 1, 0, "C", fill=True)
        pdf.cell(100, 6, "Description", 1, 0, "L", fill=True)
        pdf.cell(25, 6, "Qty", 1, 0, "C", fill=True)
        pdf.cell(30, 6, "Status", 1, 1, "C", fill=True)

        pdf.set_font("Helvetica", "", 8)
        for part in parts:
            pdf.cell(35, 5.5, str(part.get("number", "-")), 1, 0, "C")
            pdf.cell(100, 5.5, str(part.get("desc", "-")), 1, 0, "L")
            pdf.cell(25, 5.5, str(part.get("qty", "1")), 1, 0, "C")
            pdf.cell(30, 5.5, str(part.get("status", "Installed")), 1, 1, "C")
        pdf.ln(3)

    # 6. Photographic Evidence
    valid_photos = [p for p in (photos or []) if os.path.exists(p)]
    if valid_photos:
        if pdf.get_y() > 180:
            pdf.add_page()

        pdf.section_title(f"6. SITE & FAULT PHOTOGRAPHIC EVIDENCE ({len(valid_photos)} Photos)")
        
        box_w = 88
        box_h = 62
        gap_x = 10
        gap_y = 6
        x_left = 12
        x_right = x_left + box_w + gap_x

        current_y = pdf.get_y() + 2

        for idx, img_path in enumerate(valid_photos):
            col = idx % 2
            if col == 0 and idx > 0:
                current_y += box_h + gap_y

            if current_y + box_h > 265:
                pdf.add_page()
                current_y = 20

            cur_x = x_left if col == 0 else x_right

            try:
                pdf.image(img_path, x=cur_x, y=current_y, w=box_w, h=box_h, keep_aspect_ratio=True)
            except Exception as e:
                print(f"[PDF_IMAGE_ERROR] {e}")

        pdf.set_y(current_y + box_h + 6)

    # 7. Verification & Sign-off
    if pdf.get_y() > 240:
        pdf.add_page()

    pdf.ln(2)
    pdf.section_title("7. VERIFICATION & SIGN-OFF")
    pdf.ln(3)
    pdf.info_row("Service Engineer:", data.get("engineer_name", "Service Team"), "Customer Representative:", data.get("client_rep", ""), c1_w=32, c2_w=44)
    pdf.ln(8)
    pdf.info_row("Signature: ______________________", "", "Signature: ______________________", "", c1_w=50, c2_w=50)

    pdf.output(output_path)
    return output_path