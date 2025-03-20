#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
자동 단면검토 계산 및 보고서 생성 스크립트
입력 수치(단위: b, d, cover: mm; Mu: kN·m; Vu: kN; A_prov: mm²)를 입력하면,
① 필요 철근량 계산(식①, 식② 사용),
② 휨 및 전단 검토 결과 산출,
③ 각 지점부의 계산식, 결과, 검토 결과를 상세하게 기술한 보고서를 작성하고,
④ 단면 도면과 함께 Excel 및 PDF 보고서로 저장합니다.

※ PDF 한글 출력을 위해 폰트 파일들이 "fonts" 폴더 내에 있어야 합니다.
    (예: fonts/NanumGothic-Regular.ttf, fonts/NanumGothic-Bold.ttf, fonts/NanumGothic-ExtraBold.ttf)
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
    """이차방정식 a*x² + b*x + c = 0의 양의 실근 반환"""
    disc = b_coef**2 - 4 * a_coef * c_coef
    if disc < 0:
        return None
    x1 = (-b_coef + math.sqrt(disc)) / (2 * a_coef)
    x2 = (-b_coef - math.sqrt(disc)) / (2 * a_coef)
    sols = [x for x in (x1, x2) if x > 0]
    return min(sols) if sols else None

def calculate_required_As(Mu, d, b, fck, fy, phi):
    """
    필요 철근량 A_req 및 압축블록 깊이 a_req 계산
    공식(식①): Mu/φ = A_req·fy·[d – (A_req·fy)/(2·0.85·fck·b)]
    Mu : kN·m (내부 계산 시 N·mm 단위로 변환)
    d, b : mm 단위
    """
    Mu_Nmm = Mu * 1e6  # 단위 변환
    a_coef = (fy**2) / (2 * 0.85 * fck * b)
    b_coef = - fy * d
    c_coef = Mu_Nmm / phi
    A_req = solve_quadratic(a_coef, b_coef, c_coef)
    if A_req is None:
        raise ValueError("이차방정식 해가 존재하지 않습니다.")
    a_req = (A_req * fy) / (0.85 * fck * b)
    return A_req, a_req

def calculate_section_results(section, fck=27, fy=400, phi=0.85):
    """
    입력 section(딕셔너리)을 바탕으로 계산한 결과를 딕셔너리로 반환
    필수 입력 항목: 'section','b','d','cover','Mu','Vu','A_prov'
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
        phi_Mn = phi * Mn_prov
        safety = phi_Mn / (Mu * 1e6)
        ratio = A_prov / A_req
    else:
        a_prov = None
        phi_Mn = None
        safety = None
        ratio = None

    Vc = 0.80 * (1/6) * math.sqrt(fck) * b_val * d  # N
    Vc_kN = Vc / 1000
    shear_chk = "O.K" if Vc_kN >= Vu else "NG"

    results = {
        "단면": section['section'],
        "b (mm)": b_val,
        "d (mm)": d,
        "피복 (mm)": section['cover'],
        "Mu (kN·m)": Mu,
        "Vu (kN)": Vu,
        "A_prov (mm²)": A_prov,
        "필요철근량 (mm²)": round(A_req, 2),
        "a_req (mm)": round(a_req, 2),
        "a_prov (mm)": round(a_prov, 2) if a_prov is not None else None,
        "제공/필요 비율": round(ratio, 2) if ratio is not None else None,
        "φ·Mn (N·mm)": round(phi_Mn, 2) if phi_Mn is not None else None,
        "안전율": round(safety, 3) if safety is not None else None,
        "Vc (kN)": round(Vc_kN, 2),
        "전단검토": shear_chk
    }
    return results

# -------------------------------
# 2. 상세 보고서 텍스트 생성 함수
# -------------------------------

def generate_section_report(section, res):
    """
    각 단면에 대해 상세 보고서 텍스트(계산식, 결과, 검토결과 등)를 반환
    """
    s_name = section['section']
    b = section['b']
    d = section['d']
    cover = section['cover']
    Mu = section['Mu']
    Vu = section['Vu']
    A_prov = section.get('A_prov', "미입력")
    
    A_req = res["필요철근량 (mm²)"]
    a_req = res["a_req (mm)"]
    a_prov = res["a_prov (mm)"] if res["a_prov (mm)"] is not None else "N/A"
    ratio = res["제공/필요 비율"] if res["제공/필요 비율"] is not None else "N/A"
    phi_Mn = res["φ·Mn (N·mm)"] if res["φ·Mn (N·mm)"] is not None else "N/A"
    safety = res["안전율"] if res["안전율"] is not None else "N/A"
    Vc = res["Vc (kN)"]
    shear_chk = res["전단검토"]
    
    report = f"""【단면 정보】
단면 위치: {s_name}
단위폭 (b): {b} mm, 유효심 (d): {d} mm, 피복두께: {cover} mm
작용모멘트 (Mu): {Mu} kN·m, 작용전단력 (Vu): {Vu} kN
제공 철근량: {A_prov} mm²

【필요 철근량 계산】
식①: Mu/φ = A_req·fy·[d – (A_req·fy)/(2·0.85·fck·b)]
계산 결과: 필요 철근량 A_req = {A_req} mm², 압축블록 깊이 a_req = {a_req} mm

【제공 철근 평가 및 휨 설계 검토】
제공 철근량 A_prov = {A_prov} mm² → 제공/필요 비율 = {ratio}
계산된 φ·Mn = {phi_Mn} N·mm
안전율(φ·Mn/Mu) = {safety}

【전단 검토】
전단저항 Vc = {Vc} kN, 작용전단력 Vu = {Vu} kN
전단검토 결과: {shear_chk}

※ "O.K"는 설계 기준 충족을 의미합니다.
"""
    return report

# -------------------------------
# 3. 단면 도면 생성 함수 (matplotlib 활용)
# -------------------------------

def sanitize_filename(name):
    """파일명에 사용할 수 없는 문자는 언더바로 치환"""
    return re.sub(r'[\\/*?:"<>| ]', "_", name)

def draw_section_diagram(section, save_dir="diagrams"):
    """
    단면 수치(단위: mm)를 기반으로 단면 도면을 그리고 PNG 파일로 저장
    - 전체 단면: 상단(압축부)부터 하단(인장부)까지 직사각형으로 표현
    - 전체 깊이: overall_depth = d + cover
    - 효과심선: 상단에서 d의 위치에 표시
    - 철근: 단일층으로 균등 배치 (n_bars, 기본값 4)
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
# 4. PDF 보고서 생성 함수 (fpdf 활용)
# -------------------------------

class PDFReport(FPDF):
    def header(self):
        # 폰트 파일 경로에 "fonts/" 폴더를 반영
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

def create_pdf_report(df, diagram_files, section_reports, pdf_filename="section_review.pdf"):
    """
    df: 계산 결과 DataFrame (요약)
    diagram_files: dict, key: 단면 이름, value: PNG 파일 경로
    section_reports: dict, key: 단면 이름, value: 상세 보고서 텍스트
    """
    pdf = PDFReport()
    
    # 첫 페이지: 요약 표를 가로 방향(Landscape)으로 출력
    pdf.add_page(orientation="L")
    pdf.set_font("NanumGothic", "B", 10)
    pdf.cell(0, 10, "【단면검토 요약】", ln=True, align="C")
    pdf.ln(5)

    headers = list(df.columns)
    epw = pdf.w - pdf.l_margin - pdf.r_margin  # 유효 페이지 너비
    col_width = epw / len(headers)  # 각 열의 너비를 동일하게 분배
    row_height = 8  # 행 높이

    # 헤더 출력 (회색 배경)
    pdf.set_fill_color(200, 200, 200)
    for header in headers:
        pdf.cell(col_width, row_height, header, border=1, align="C", fill=True)
    pdf.ln(row_height)

    # 데이터 행 출력 (각 셀은 한 줄로 출력)
    pdf.set_font("NanumGothic", "", 9)
    for _, row in df.iterrows():
        for header in headers:
            cell_text = str(row[header])
            pdf.cell(col_width, row_height, cell_text, border=1, align="C")
        pdf.ln(row_height)

    # 각 단면별 상세 보고서 페이지
    for sec_name in section_reports:
        pdf.add_page()
        pdf.set_font("NanumGothic", "B", 14)
        pdf.cell(0, 10, f"단면검토 : {sec_name}", ln=True)
        pdf.ln(3)
        pdf.set_font("NanumGothic", "", 10)
        pdf.multi_cell(0, 6, section_reports[sec_name])
        pdf.ln(3)
        if sec_name in diagram_files:
            pdf.image(diagram_files[sec_name], x=30, w=150)

    pdf.output(pdf_filename)

# -------------------------------
# 5. 메인 코드: 입력, 계산, 보고서 생성, Excel 및 PDF 저장
# -------------------------------

if __name__ == '__main__':
    sections = [
        {"section": "좌측단부", "b": 1000, "d": 720, "cover": 80, "Mu": 63.28, "Vu": 368.45, "A_prov": 5745.5, "n_bars": 10},
        {"section": "중앙부(지간1)", "b": 1000, "d": 740, "cover": 60, "Mu": 1043.88, "Vu": 0.0,    "A_prov": 5745.5, "n_bars": 10},
        {"section": "중간지점1",  "b": 1000, "d": 1020, "cover": 80, "Mu": 1827.32, "Vu": 524.70, "A_prov": 6424.0, "n_bars": 10},
        {"section": "중앙부(지간2)", "b": 1000, "d": 740, "cover": 60, "Mu": 1206.20, "Vu": 0.0,    "A_prov": 6424.0, "n_bars": 10},
        {"section": "중간지점2",  "b": 1000, "d": 1020, "cover": 80, "Mu": 1823.82, "Vu": 524.43, "A_prov": 6424.0, "n_bars": 10},
        {"section": "중앙부(지간3)", "b": 1000, "d": 740, "cover": 60, "Mu": 1036.81, "Vu": 0.0,    "A_prov": 5745.5, "n_bars": 10},
        {"section": "우측단부", "b": 1000, "d": 720, "cover": 80, "Mu": 63.28, "Vu": 368.45, "A_prov": 5745.5, "n_bars": 10},
    ]
    
    results_list = []
    diagram_files = {}
    section_reports = {}
    
    for sec in sections:
        res = calculate_section_results(sec, fck=27, fy=400, phi=0.85)
        results_list.append(res)
        section_reports[sec['section']] = generate_section_report(sec, res)
        diag_file = draw_section_diagram(sec, save_dir="diagrams")
        diagram_files[sec['section']] = diag_file
    
    df_results = pd.DataFrame(results_list)
    excel_filename = "section_review.xlsx"
    df_results.to_excel(excel_filename, index=False)
    print(f"Excel 파일로 저장됨: {excel_filename}")
    
    pdf_filename = "section_review.pdf"
    create_pdf_report(df_results, diagram_files, section_reports, pdf_filename=pdf_filename)
    print(f"PDF 파일로 저장됨: {pdf_filename}")
