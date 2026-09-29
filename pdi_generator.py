import os
from fpdf import FPDF

class PDIPDF(FPDF):
    def header(self):
        self.set_fill_color(248, 250, 252)
        self.rect(10, 8, 190, 22, "F")
        
        self.set_xy(14, 11)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(220, 38, 38)
        self.cell(30, 7, "Linde", 0, 0, "L")
        
        self.set_xy(48, 10)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(15, 23, 42)
        self.cell(100, 6, "PRE-DELIVERY INSPECTION (PDI)", 0, 1, "L")
        self.set_x(48)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(100, 4, "Quality Assurance & Commissioning Certificate", 0, 0, "L")
        
        self.set_xy(150, 11)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 41, 59)
        self.cell(45, 7, "MCV", 0, 0, "R")

        self.set_y(32)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 6, f"Page {self.page_no()}/{{nb}} - Linde Official Pre-Delivery Record", align="C")

def section_bar(pdf, title):
    pdf.ln(2)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(190, 5.5, f"  {title}", fill=True, border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)

def generate_pdi_pdf(data, output_path):
    pdf = PDIPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    section_bar(pdf, "1. EQUIPMENT & INSPECTION RECORD")
    
    w_lbl, w_val = 35, 60
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(71, 85, 105)
    
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(w_lbl, 6, "Truck Serial No:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, str(data.get("serial_no", "-")), 1, 0, "L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Inspection Date:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, str(data.get("date", "-")), 1, 1, "L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Truck Category:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, str(data.get("truck_type", "-")), 1, 0, "L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Operating KM / Hours:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, str(data.get("km_hours", "-")), 1, 1, "L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Inspection Time:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, f"{data.get('start_time','-')} to {data.get('finish_time','-')}", 1, 0, "L")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_lbl, 6, "Worked / Travelled:", 1, 0, "L", True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_val, 6, f"{data.get('time_worked','-')} / {data.get('time_travelled','-')}", 1, 1, "L")
    pdf.ln(2)

    section_bar(pdf, "2. COMPLETED QUALITY VERIFICATION CHECKLIST")
    checked_items = data.get("checked_items", [])
    
    col_w = 93
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(30, 41, 59)

    for i in range(0, len(checked_items), 2):
        item1 = checked_items[i]
        pdf.cell(col_w, 5.5, f"  [ PASS ]  {item1}", border=1)
        pdf.cell(4, 5.5, "", 0, 0)
        if i + 1 < len(checked_items):
            item2 = checked_items[i+1]
            pdf.cell(col_w, 5.5, f"  [ PASS ]  {item2}", border=1, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.ln(5.5)

    pdf.ln(3)

    section_bar(pdf, "3. HANDOVER AUTHORIZATION & SIGN-OFF")
    sig_y = pdf.get_y() + 2

    pdf.set_xy(10, sig_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(90, 5, "Certified Quality Inspector:", 0, 1, "L")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(90, 4, "Signature:", 0, 1, "L")
    pdf.rect(10, sig_y + 9, 90, 22)

    sig_path = data.get("sig_path")
    if sig_path and os.path.exists(sig_path):
        try:
            pdf.image(sig_path, x=25, y=sig_y + 10, w=50, h=18)
        except Exception:
            pass

    pdf.set_xy(110, sig_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(90, 5, "Handover Approval Status:", 0, 1, "L")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(90, 5, "PASSED & APPROVED FOR DELIVERY", 0, 1, "L")
    pdf.rect(110, sig_y + 9, 90, 22)
    pdf.set_xy(114, sig_y + 20)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(80, 4, "Linde Quality Assurance Stamp & Verification", 0, 0, "C")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pdf.output(output_path)
    return output_path
