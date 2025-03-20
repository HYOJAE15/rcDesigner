#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
자동 단면검토 계산 및 보고서 생성 스크립트
입력 수치 (단위: b, d, cover: mm; Mu: kN·m; Vu: kN; A_prov: mm²)를 입력하면
① 필요 철근량 계산, 제공 철근과의 비율, 휨/전단 검토 결과 산출
② 각 단면의 도면(외곽, 효과심선, 철근 배치)을 생성
③ 계산 결과를 Excel 파일과 단면 도면 및 계산표가 포함된 PDF 보고서로 저장

※ PDF에 한글을 출력하기 위해 NanumGothic 계열의 TrueType 글꼴 파일을 사용합니다.
   예: NanumGothic-Regular.ttf, NanumGothic-Bold.ttf, NanumGothic-ExtraBold.ttf
   해당 파일들을 스크립트와 동일한 폴더에 위치시키세요.
"""

import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from fpdf import FPDF
import os
import re

# -------------------------------
# 1. 계산 관련 함수 정의
# -------------------------------

def solve_quadratic(a_coef, b_coef, c_coef):
    """
    이차방정식 a*x^2 + b*x + c = 0 의 실근(양의 값)을 반환 (없으면 None)
    """
    discriminant = b_coef**2 - 4*a_coef*c_coef
    if discriminant < 0:
        return None
    x1 = (-b_coef + math.sqrt(discriminant)) / (2*a_coef)
    x2 = (-b_coef - math.sqrt(discriminant)) / (2*a_coef)
    sol = [x for x in (x1, x2) if x > 0]
    if sol:
        return min(sol)
    else:
        return None

def calculate_required_As(Mu, d, b, fck, fy, phi):
    """
    필요 철근량(A_req) 계산 함수
    Mu : 작용모멘트 (kN·m) → 내부 계산은 N·mm 단위로 변환
    d  : 유효심 (mm)
    b  : 단위폭 (mm)
    fck: 콘크리트 압축강도 (MPa)
    fy : 철근 항복강도 (MPa)
    phi: 강도감소계수
    공식: Mu/phi = A_req·fy·[d – (A_req·fy)/(2·0.85·fck·b)]
    """
    Mu_Nmm = Mu * 1e6  # kN·m → N·mm
    a_coef = (fy**2) / (2 * 0.85 * fck * b)
    b_coef = - fy * d
    c_coef = Mu_Nmm / phi
    A_req = solve_quadratic(a_coef, b_coef, c_coef)
    if A_req is None:
        raise ValueError("이차방정식의 해가 존재하지 않습니다.")
    a_val = (A_req * fy) / (0.85 * fck * b)
    return A_req, a_val

def calculate_section_results(section, fck=27, fy=400, phi=0.85):
    """
    단면별 계산 결과 도출 함수
    section: dict – 반드시 포함해야 할 항목:
         'section' : 단면 이름 (예: "좌측단부")
         'b'       : 단위폭 (mm)
         'd'       : 유효심 (mm)
         'cover'   : 철근 피복 두께 (mm)
         'Mu'      : 작용모멘트 (kN·m)
         'Vu'      : 작용전단력 (kN)
         'A_prov'  : 제공 철근량 (mm²)
         (옵션) 'n_bars': 철근 수 (단일층, 기본값 4)
    반환: dict – 계산 결과 항목들
    """
    b_val = section['b']
    d = section['d']
    Mu = section['Mu']
    Vu = section['Vu']
    A_prov = section.get('A_prov', None)

    A_req, a_req = calculate_required_As(Mu, d, b_val, fck, fy, phi)
    
    if A_prov is not None:
        a_prov = (A_prov * fy) / (0.85 * fck * b_val)
        Mn_prov = A_prov * fy * (d - a_prov/2)
        phi_Mn_prov = phi * Mn_prov
        safety_flex = phi_Mn_prov / (Mu * 1e6)
    else:
        a_prov = None
        phi_Mn_prov = None
        safety_flex = None

    Vc = 0.80 * (1/6) * math.sqrt(fck) * b_val * d   # N
    Vc_kN = Vc / 1000
    shear_check = "O.K" if Vc_kN >= Vu else "NG"
    reinforcement_ratio = A_prov / A_req if A_prov is not None else None

    results = {
        "단면": section['section'],
        "필요철근량 (mm²)": round(A_req, 2),
        "제공철근량 (mm²)": round(A_prov, 2) if A_prov is not None else None,
        "제공/필요 비율": round(reinforcement_ratio, 2) if reinforcement_ratio is not None else None,
        "a_req (mm)": round(a_req, 2),
        "a_prov (mm)": round(a_prov, 2) if a_prov is not None else None,
        "φ·Mn (N·mm)": round(phi_Mn_prov, 2) if phi_Mn_prov is not None else None,
        "Mu (N·mm)": round(Mu*1e6, 2),
        "안전율": round(safety_flex, 3) if safety_flex is not None else None,
        "Vc (kN)": round(Vc_kN, 2),
        "Vu (kN)": Vu,
        "전단검토": shear_check
    }
    return results

# -------------------------------
# 2. 단면 도면 생성 함수 (matplotlib 활용)
# -------------------------------

def sanitize_filename(name):
    """파일명에 사용할 수 없는 문자는 언더바로 치환"""
    return re.sub(r'[\\/*?:"<>| ]', "_", name)

def draw_section_diagram(section, save_dir="diagrams"):
    """
    단면 수치(단위: mm)를 기반으로 단면 도면을 그리고 PNG 파일로 저장.
    - 전체 단면: 상단(압축부)부터 하단(인장부)까지의 직사각형
    - 전체 깊이: overall_depth = d + cover
    - 효과심선은 상단에서 d 위치에 표시
    - 철근은 단일층으로 균등 배치 (n_bars, 기본 4)
    """
    b = section['b']
    d = section['d']
    cover = section.get('cover', 50)
    n_bars = section.get('n_bars', 4)
    overall_depth = d + cover

    fig_width = b / 300
    fig_height = overall_depth / 300
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    rect = Rectangle((0, 0), b, overall_depth, fill=False, edgecolor="black", linewidth=1.5)
    ax.add_patch(rect)
    
    ax.plot([0, b], [d, d], "k--", linewidth=1)
    ax.text(b*0.02, d - 10, "d", fontsize=10, color="blue")
    
    bar_x = np.linspace(cover, b - cover, n_bars)
    bar_y = d
    bar_radius = 0.02 * b if 0.02 * b > 5 else 5
    for x in bar_x:
        circ = Circle((x, bar_y), bar_radius, color="red", fill=True)
        ax.add_patch(circ)
    
    ax.annotate("", xy=(0, overall_depth+10), xytext=(b, overall_depth+10),
                arrowprops=dict(arrowstyle="<->", color="green"))
    ax.text(b/2, overall_depth+15, f"b = {b} mm", fontsize=10, color="green", ha="center")
    ax.annotate("", xy=(-10, 0), xytext=(-10, overall_depth),
                arrowprops=dict(arrowstyle="<->", color="green"))
    ax.text(-20, overall_depth/2, f"h = {overall_depth} mm", fontsize=10, color="green", va="center", rotation=90)
    
    ax.set_xlim(-40, b+40)
    ax.set_ylim(-40, overall_depth+40)
    ax.invert_yaxis()
    ax.axis("off")
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    filename = os.path.join(save_dir, f"section_{sanitize_filename(section['section'])}.png")
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return filename

# -------------------------------
# 3. PDF 보고서 생성 함수 (fpdf 활용)
# -------------------------------

class PDFReport(FPDF):
    def header(self):
        # 한글 지원을 위해 NanumGothic 폰트 계열을 등록
        self.add_font("NanumGothic", "", "fonts/NanumGothic-Regular.ttf", uni=True)
        self.add_font("NanumGothic", "B", "fonts/NanumGothic-Bold.ttf", uni=True)
        self.add_font("NanumGothic", "EB", "fonts/NanumGothic-ExtraBold.ttf", uni=True)
        self.set_font("NanumGothic", "B", 16)
        self.cell(0, 10, "단면검토 결과 보고서", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("NanumGothic", "", 8)
        self.cell(0, 10, f"페이지 {self.page_no()}", 0, 0, "C")

def create_pdf_report(df, diagram_files, pdf_filename="section_review.pdf"):
    """
    df: 계산 결과 DataFrame
    diagram_files: dict, key: 단면 이름, value: PNG 파일 경로
    """
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("NanumGothic", "", 10)
    
    # 계산 결과 표: 12개 열에 맞게 col_widths 설정
    col_widths = [20, 25, 25, 25, 20, 20, 30, 30, 20, 20, 20, 20]
    headers = list(df.columns)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, str(header), border=1, align="C")
    pdf.ln()
    
    for idx, row in df.iterrows():
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, str(row[header]), border=1, align="C")
        pdf.ln()
    
    for section, img_file in diagram_files.items():
        pdf.add_page()
        pdf.set_font("NanumGothic", "B", 14)
        pdf.cell(0, 10, f"단면 도면: {section}", ln=True, align="C")
        pdf.ln(5)
        pdf.image(img_file, x=30, y=None, w=150)
    
    pdf.output(pdf_filename)

# -------------------------------
# 4. 메인 코드: 입력, 계산, 도면 생성, Excel 및 PDF 저장
# -------------------------------

if __name__ == '__main__':
    sections = [
        {"section": "좌측단부", "b": 1000, "d": 720, "cover": 80, "Mu": 63.28, "Vu": 368.45, "A_prov": 5745.5, "n_bars": 10},
        {"section": "중앙부(지간1)", "b": 1000, "d": 740, "cover": 60, "Mu": 1043.88, "Vu": 0.0, "A_prov": 5745.5, "n_bars": 10},
        {"section": "중간지점1", "b": 1000, "d": 1020, "cover": 80, "Mu": 1827.32, "Vu": 524.70, "A_prov": 6424.0, "n_bars": 10},
        {"section": "중앙부(지간2)", "b": 1000, "d": 740, "cover": 60, "Mu": 1206.20, "Vu": 0.0, "A_prov": 6424.0, "n_bars": 10},
        {"section": "중간지점2", "b": 1000, "d": 1020, "cover": 80, "Mu": 1823.82, "Vu": 524.43, "A_prov": 6424.0, "n_bars": 10},
        {"section": "중앙부(지간3)", "b": 1000, "d": 740, "cover": 60, "Mu": 1036.81, "Vu": 0.0, "A_prov": 5745.5, "n_bars": 10},
        {"section": "우측단부", "b": 1000, "d": 720, "cover": 80, "Mu": 63.28, "Vu": 368.45, "A_prov": 5745.5, "n_bars": 10},
    ]
    
    results_list = []
    diagram_files = {}
    
    for sec in sections:
        res = calculate_section_results(sec, fck=27, fy=400, phi=0.85)
        results_list.append(res)
        diagram_file = draw_section_diagram(sec, save_dir="diagrams")
        diagram_files[sec['section']] = diagram_file
    
    df_results = pd.DataFrame(results_list)
    excel_filename = "section_review.xlsx"
    df_results.to_excel(excel_filename, index=False)
    print(f"Excel 파일로 저장됨: {excel_filename}")
    
    pdf_filename = "section_review.pdf"
    create_pdf_report(df_results, diagram_files, pdf_filename=pdf_filename)
    print(f"PDF 파일로 저장됨: {pdf_filename}")
