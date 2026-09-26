import os
from datetime import datetime
from fpdf import FPDF

class ServiceReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 41, 59)
        self.cell(0, 8, "FIELD SERVICE REPORT", border=0, new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, "Technical Maintenance & Equipment Inspection", border=0, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(4)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} - Confidential Technical Service Record", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(241, 245, 249)
        self.set_text_color(15, 23, 42)
        self.cell(0, 7, f"  {title}", border=0, new_x="LMARGIN", new_y="NEXT", align="L", fill=True)
        self.ln(2)

    def info_row(self, col1_title, col1_val, col2_title, col2_val):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(71, 85, 105)
        self.cell(32, 6, col1_title, border=0)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(15, 23, 42)
        self.cell(63, 6, str(col1_val or "-"), border=0)

        self.set_font("Helvetica", "B", 9)
        self.set_text_color(71, 85, 105)
        self.cell(32, 6, col2_title, border=0)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(15, 23, 42)
        self.cell(63, 6, str(col2_val or "-"), border=0, new_x="LMARGIN", new_y="NEXT")


def generate_service_pdf(data, output_path, photos=None):
    pdf = ServiceReportPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Meta Info Box
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(95, 6, f"Report ID: {data.get('report_id', 'SR-PENDING')}", border=0)
    pdf.cell(95, 6, f"Date: {data.get('date', datetime.today().strftime('%Y-%m-%d'))}", border=0, new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(2)

    # 1. Client Information
    pdf.section_title("1. CLIENT & SITE DETAILS")
    pdf.info_row("Client Name:", data.get("client_name"), "Site / Branch:", data.get("site_location"))
    pdf.info_row("Contact Person:", data.get("contact_person"), "Contact Phone:", data.get("contact_phone"))
    pdf.ln(3)

    # 2. Equipment Information
    pdf.section_title("2. MACHINE SPECIFICATIONS")
    pdf.info_row("Equipment Model:", data.get("model"), "Serial Number:", data.get("serial_number"))
    pdf.info_row("Operating Hours:", data.get("hours"), "Service Type:", data.get("service_type", "Corrective"))
    pdf.ln(3)

    # 3. Technical Findings & Root Cause
    pdf.section_title("3. ISSUE DESCRIPTION & ROOT CAUSE")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, data.get("reported_issue", "No defect description logged."))
    pdf.ln(3)

    # 4. Corrective Action Taken
    pdf.section_title("4. ACTIONS TAKEN & REMARKS")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, data.get("actions_taken", "Inspection and testing carried out."))
    pdf.ln(3)

    # 5. Spare Parts Table (if any)
    parts = data.get("parts", [])
    if parts:
        pdf.section_title("5. REPLACED / REQUIRED SPARE PARTS")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(226, 232, 240)
        pdf.cell(35, 6, "Part Number", 1, 0, "C", fill=True)
        pdf.cell(105, 6, "Description", 1, 0, "L", fill=True)
        pdf.cell(25, 6, "Qty", 1, 0, "C", fill=True)
        pdf.cell(25, 6, "Status", 1, 1, "C", fill=True)

        pdf.set_font("Helvetica", "", 8)
        for part in parts:
            pdf.cell(35, 6, str(part.get("number", "-")), 1, 0, "C")
            pdf.cell(105, 6, str(part.get("desc", "-")), 1, 0, "L")
            pdf.cell(25, 6, str(part.get("qty", "1")), 1, 0, "C")
            pdf.cell(25, 6, str(part.get("status", "Installed")), 1, 1, "C")
        pdf.ln(4)

    # 6. Embedded Photos (Optional)
    if photos:
        valid_photos = [p for p in photos if os.path.exists(p)]
        if valid_photos:
            pdf.section_title("6. SITE & FAULT PHOTOGRAPHIC EVIDENCE")
            x_start = 15
            y_start = pdf.get_y()
            img_w = 85
            img_h = 60

            for idx, img_path in enumerate(valid_photos[:4]):
                col = idx % 2
                row = idx // 2
                pos_x = x_start + (col * (img_w + 10))
                pos_y = y_start + (row * (img_h + 8))

                if pos_y + img_h > 270:
                    pdf.add_page()
                    pos_y = 20

                pdf.image(img_path, x=pos_x, y=pos_y, w=img_w, h=img_h)

            pdf.set_y(pos_y + img_h + 8)

    # 7. Signatures / Confirmation
    if pdf.get_y() > 240:
        pdf.add_page()

    pdf.ln(4)
    pdf.section_title("7. VERIFICATION & SIGN-OFF")
    pdf.ln(4)

    pdf.info_row("Service Engineer:", data.get("engineer_name", "Service Team"), "Customer Representative:", data.get("client_rep", ""))
    pdf.ln(8)
    pdf.info_row("Signature: __________________", "", "Signature: __________________", "")

    # Save output
    pdf.output(output_path)
    return output_path
