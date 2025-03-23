import pandas as pd
import os
from fpdf import FPDF
import math

def ensure_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

ensure_folder("result")

class SectionReportPDF(FPDF):
    def header(self):
        # 한글 폰트 등록 (uni 인자는 fpdf2에서 무시됨)
        self.add_font("NanumGothic", "", "fonts/NanumGothic-Regular.ttf", uni=True)
        self.add_font("NanumGothic", "B", "fonts/NanumGothic-Bold.ttf", uni=True)
        self.set_font("NanumGothic", "B", 16)
        title = self.title if hasattr(self, "title") else "【 단면검토 보고서 】"
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(3)
    
    def footer(self):
        self.set_y(-15)
        self.set_font("NanumGothic", "", 10)
        self.cell(0, 10, f"페이지 {self.page_no()}", new_x="LMARGIN", new_y="NEXT", align="C")

# 필요철근량 계산함수 (실제 계산식)
def calculate_required_rebar(Mu, fy, d, fck, b, phi_s=0.9, phi_c=0.65, alpha=0.8, beta=0.85):
    Mu_Nmm = Mu * 1e6
    a = phi_s * fy
    b_coef = -(phi_s * fy * d)
    c_coef = Mu_Nmm / (0.85 * alpha * phi_c * fck * b)

    discriminant = b_coef**2 - 4 * a * (-c_coef)
    As = (-b_coef - math.sqrt(discriminant)) / (2 * a)
    c = (As * phi_s * fy) / (alpha * phi_c * 0.85 * fck * b)
    return As, c

# 상세보고서 페이지 추가 함수
def create_section_page(pdf, section):
    pdf.add_page()
    pdf.title = f"【 단면검토 : {section['section']} 】"
    pdf.set_font("NanumGothic", "", 10)

    # [단면제원]
    spec_text = (
        "[1. 단면제원 및 설계가정]\n"
        f"B = {section['b (mm)']} mm, H = {section['H (mm)']} mm, d = {section['d (mm)']} mm, cover = {section['cover (mm)']} mm\n"
        f"Mu = {section['Mu (kN·m)']} kN·m, Vu = {section['Vu (kN)']} kN, A_prov = {section['A_prov (mm²)']} mm²\n"
        f"fck = {section['fck (MPa)']} MPa, fy = {section['fy (MPa)']} MPa, fvy = {section['fvy (MPa)']} MPa"
    )
    pdf.multi_cell(0, 6, spec_text)
    pdf.ln(4)

    # [필요철근량 산정] - 실제 계산 수행
    As, c = calculate_required_rebar(section['Mu (kN·m)'], section['fy (MPa)'], section['d (mm)'], section['fck (MPa)'], section['b (mm)'])
    As_text = (
        "[2. 필요철근량 산정]\n"
        f"Mu=As·Φs·fy·(d-β·c), c=(As·Φs·fy)/(α·Φc·0.85·fck·b)\n"
        f"계산된 필요 철근량 As = {As:.2f} mm², 중립축 깊이 c = {c:.2f} mm"
    )
    pdf.multi_cell(0, 6, As_text)
    pdf.ln(4)

    # [철근량 검토]
    As_min = max(0.0014 * section['b (mm)'] * section['d (mm)'], 0.25 * (section['fck (MPa)']**0.5 / section['fy (MPa)']) * section['b (mm)'] * section['d (mm)'])
    rebar_check = "O.K" if section['A_prov (mm²)'] >= As_min else "N.G"
    rebar_text = (
        "[3. 철근량 검토]\n"
        f"As,min = {As_min:.2f} mm², 제공 철근량 = {section['A_prov (mm²)']} mm²\n"
        f"검토 결과: {rebar_check}"
    )
    pdf.multi_cell(0, 6, rebar_text)
    pdf.ln(4)

    # 추가 검토 항목들을 동일한 방식으로 구현 (생략)

def create_pdf_from_excel(excel_path, output_path):
    xls = pd.ExcelFile(excel_path)
    pdf = SectionReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        for _, row in df.iterrows():
            create_section_page(pdf, row)

    pdf.output(output_path)
    print(f"PDF 보고서가 '{output_path}'로 저장되었습니다.")

if __name__ == "__main__":
    excel_input = "section_data_template.xlsx"
    pdf_output = "result/multi_section_report.pdf"
    create_pdf_from_excel(excel_input, pdf_output)
