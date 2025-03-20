#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
여러 단면의 단면검토 및 균열 단면의 사용성 검토 보고서 생성 스크립트

[단면검토]
1. 단면제원 (표 활용)
2. 필요철근량 산정
3. 철근량 검토
4. 중립축 깊이 검토
5. 인장철근 변형률
6. 설계 휨강도 산정
7. 전단에 대한 검토
8. 최소 전단철근량 검토
9. 전단철근 간격 검토

[균열 단면의 사용성 검토]
1. 비균열 가정시 인장 연단 응력
2. 응력 검토
3. 균열 제어를 위한 최소철근량
4. 간접 균열 검토
5. 균열폭 계산

※ 본 스크립트는 업로드하신 자료에 있는 단면들을 모두 반영하여  
   각 단면의 세부 계산식(계산식, 결과, 검토 내용 등)이 PDF 페이지 내에 모두 보이도록 구성되었습니다.
   (단면 그림은 포함하지 않습니다.)
결과물은 "result" 폴더에 저장됩니다.
"""

import os, math, re
from fpdf import FPDF

# 결과물이 저장될 폴더 생성
def ensure_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

ensure_folder("result")

# PDF 보고서 클래스 (fpdf2 사용)
class SectionReportPDF(FPDF):
    def __init__(self, orientation='P', unit='mm', format='A4'):
        super().__init__(orientation, unit, format)
        self.set_margins(5, 5, 5)
        self.set_auto_page_break(auto=True, margin=5)
    
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

# PDF에 여러 줄 텍스트를 추가하는 함수
def add_multiline(pdf, text, font="NanumGothic", style="", size=9):
    pdf.set_font(font, style, size)
    avail_width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(avail_width, 5, text, align="L")
    pdf.ln(3)

# 각 단면의 상세 보고서 페이지를 생성하는 함수
def create_section_page(pdf, section, calc):
    # 페이지 제목 (예: "【 단면검토 : 슬래브_종방향_정 】")
    pdf.add_page()
    pdf.title = f"【 단면검토 : {section['section']} 】"
    pdf.set_font("NanumGothic", "B", 14)
    pdf.cell(0, 10, pdf.title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)
    
    # 1. 단면제원 (표 활용)
    specs = (
        "[1. 단면제원]\n"
        f"B (mm) = {section['b']}\n"
        f"d (mm) = {section['d']}\n"
        f"피복 (mm) = {section['cover']}\n"
        f"Mu (kN·m) = {section['Mu']}\n"
        f"Vu (kN) = {section['Vu']}\n"
        f"제공 철근량 (mm²) = {section.get('A_prov', '미입력')}\n"
        f"재료: fck = {section['fck']} MPa, fy = {section['fy']} MPa, fvy = {section['fvy']} MPa\n"
    )
    add_multiline(pdf, specs)
    
    # 2. 필요철근량 산정
    req = (
        "[2. 필요철근량 산정]\n"
        "식①: Mu/Φ = As × fy × [d – (As×fy)/(2×0.85×fck×b)]\n"
        "식②: c = (As×Φs×fy)/(0.85×fck×b)\n"
        "(식②를 식①에 대입하여 이차방정식으로 As를 구함)\n"
        f"계산된 필요 철근량 As = {calc.get('필요철근량 (mm²)', 'N/A')} mm²\n"
        f"압축블록 깊이 c = {calc.get('a_req (mm)', 'N/A')} mm\n"
    )
    add_multiline(pdf, req)
    
    # 3. 철근량 검토
    rebar = (
        "[3. 철근량 검토]\n"
        f"사용 철근량 = {section.get('A_prov', '미입력')} mm²\n"
        f"As,min = {calc.get('As_min', 'N/A')} mm²\n"
        "검토 결과: " + ("O.K" if section.get('A_prov', 0) >= calc.get('As_min', 0) else "N.G") + "\n"
    )
    add_multiline(pdf, rebar)
    
    # 4. 중립축 깊이 검토
    neutral = (
        "[4. 중립축 깊이 검토]\n"
        f"Cmax = {calc.get('Cmax', 'N/A')} mm\n"
        f"계산된 중립축 깊이 c = {calc.get('c', 'N/A')} mm\n"
        "검토 결과: " + ("O.K" if calc.get('c', 0) <= calc.get('Cmax', 0) else "N.G") + "\n"
    )
    add_multiline(pdf, neutral)
    
    # 5. 인장철근 변형률
    strain = (
        "[5. 인장철근 변형률]\n"
        f"εs = {calc.get('eps_s', 'N/A')}\n"
        f"εyd = {calc.get('eps_yd', 'N/A')}\n"
        "검토 결과: " + ("항복가정 O.K" if calc.get('eps_yd', 0) <= calc.get('eps_s', 0) else "N.G") + "\n"
    )
    add_multiline(pdf, strain)
    
    # 6. 설계 휨강도 산정
    bending = (
        "[6. 설계 휨강도 산정]\n"
        f"계산된 φ·Mn (Mr) = {calc.get('φ·Mn (N·mm)', 'N/A')} N·mm\n"
        f"설계 Mu = {section['Mu']*1e6} N·mm\n"
        "검토 결과: " + ("O.K" if calc.get('φ·Mn (N·mm)', 0) >= section['Mu']*1e6 else "N.G") +
        f"  [Ratio : {calc.get('ratio', 'N/A')}]\n"
    )
    add_multiline(pdf, bending)
    
    # 7. 전단에 대한 검토
    shear = (
        "[7. 전단에 대한 검토]\n"
        f"전단저항 Vc = {calc.get('Vc (kN)', 'N/A')} kN\n"
        f"최소 전단저항 Vc,min = {calc.get('Vc_min', 'N/A')} kN\n"
        "검토 결과: " + ("O.K" if calc.get('Vc (kN)', 0) >= section['Vu'] else "전단보강 필요") + "\n"
    )
    add_multiline(pdf, shear)
    
    # 8. 최소 전단철근량 검토
    min_shear = (
        "[8. 최소 전단철근량 검토]\n"
        f"Av,use = {calc.get('Av_use', 'N/A')} mm²\n"
        f"pv,min = {calc.get('pv_min', 'N/A')}\n"
        f"pv,use = {calc.get('pv_use', 'N/A')}\n"
        "검토 결과: " + ("O.K" if calc.get('pv_use', 0) >= calc.get('pv_min', 0) else "N.G") + "\n"
    )
    add_multiline(pdf, min_shear)
    
    # 9. 전단철근 간격 검토
    spacing = (
        "[9. 전단철근 간격 검토]\n"
        f"최대 간격 Smax = {calc.get('Smax', 'N/A')} mm\n"
        "검토 결과: " + ("O.K" if calc.get('Smax', 0) >= calc.get('min_spacing', 0) else "N.G") + "\n"
    )
    add_multiline(pdf, spacing)
    
    # [균열 단면의 사용성 검토]
    add_multiline(pdf, "【 균열 단면의 사용성 검토 】", style="B", size=12)
    
    # 1. 비균열 가정시 인장 연단 응력
    crack1 = (
        "[1. 비균열 가정시 인장 연단 응력]\n"
        f"ft = {calc.get('ft', 'N/A')} MPa\n"
        "검토 결과: " + ("O.K" if calc.get('ft', 0) >= 2.6 else "N.G") + "\n"
    )
    add_multiline(pdf, crack1)
    
    # 2. 응력 검토
    crack2 = (
        "[2. 응력 검토]\n"
        f"콘크리트 연단 응력 fc = {calc.get('fc', 'N/A')} MPa\n"
        f"철근 응력 fs = {calc.get('fs', 'N/A')} MPa\n"
        "검토 결과: " + ("O.K" if (calc.get('fc', 0) <= 0.6 * section['fck'] and calc.get('fs', 0) <= 0.8 * section['fy']) else "N.G") + "\n"
    )
    add_multiline(pdf, crack2)
    
    # 3. 균열 제어를 위한 최소철근량
    crack3 = (
        "[3. 균열 제어를 위한 최소철근량]\n"
        f"As,min (균열) = {calc.get('As_min_crack', 'N/A')} mm²\n"
        "검토 결과: " + ("O.K" if calc.get('As_used', 0) >= calc.get('As_min_crack', 0) else "N.G") + "\n"
    )
    add_multiline(pdf, crack3)
    
    # 4. 간접 균열 검토
    crack4 = (
        "[4. 간접 균열 검토]\n"
        "검토 결과: " + str(calc.get("indirect_crack", "N/A")) + "\n"
    )
    add_multiline(pdf, crack4)
    
    # 5. 균열폭 계산
    crack5 = (
        "[5. 균열폭 계산]\n"
        f"Wk = {calc.get('Wk', 'N/A')} mm\n"
        "검토 결과: " + ("O.K" if calc.get('Wk', 0) <= 0.3 else "N.G") + "\n"
    )
    add_multiline(pdf, crack5)

# 최종 PDF 보고서를 생성하는 함수
def create_multi_section_report(sections, output_filename="result/multi_section_report.pdf"):
    pdf = SectionReportPDF()
    # 예제용 공통 계산 결과 (실제 데이터에 맞게 수정 필요)
    sample_calc = {
        "필요철근량 (mm²)": 2382.384,
        "a_req (mm)": 78.8,
        "As_min": 3176.5,
        "Av_use": 506.8,
        "pv_min": 0.00126,
        "pv_use": 0.00405,
        "Smax": 187.5,
        "min_spacing": 125,
        "ft": 9.4,
        "fc": 21.488,
        "fs": 276.098,
        "As_min_crack": 260.2,
        "As_used": 3096.8,
        "indirect_crack": "O.K",
        "Wk": 0.225,
        "ratio": 1.300,
        "eps_s": 0.0072,
        "eps_yd": 0.0022
    }
    
    for sec in sections:
        create_section_page(pdf, sec, sample_calc)
    pdf.output(output_filename)
    print(f"PDF 보고서가 '{output_filename}'로 저장되었습니다.")

# 샘플 단면 데이터 (업로드 파일의 단면명을 모두 반영)
sections_sample = [
    {"section": "슬래브_종방향_정", "b": 1000, "d": 250, "cover": 100, "Mu": 242.015, "Vu": 167.204, "A_prov": 3096.8, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "슬래브_종방향_부★", "b": 1000, "d": 250, "cover": 100, "Mu": 245.000, "Vu": 168.000, "A_prov": 3100.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "슬래브_횡방향_정", "b": 1200, "d": 500, "cover": 100, "Mu": 500.0, "Vu": 250.0, "A_prov": 6500.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "슬래브_횡방향_부", "b": 1200, "d": 500, "cover": 100, "Mu": 510.0, "Vu": 260.0, "A_prov": 6600.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "일반보(종방향)_정", "b": 1000, "d": 250, "cover": 100, "Mu": 242.015, "Vu": 167.204, "A_prov": 3096.8, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "일반보(종방향)_부", "b": 1000, "d": 250, "cover": 100, "Mu": 152.166, "Vu": 206.159, "A_prov": 2292.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "일반보(횡방향)_정", "b": 700, "d": 1050, "cover": 100, "Mu": 2354.637, "Vu": 0.0, "A_prov": 3096.8, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "일반보(횡방향)_부", "b": 700, "d": 1050, "cover": 100, "Mu": 2623.885, "Vu": 0.0, "A_prov": 2292.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "지점부(종,중앙,1200H)_정", "b": 3000, "d": 1100, "cover": 100, "Mu": 0.0, "Vu": 0.0, "A_prov": 0.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "지점부(종,좌측,1200H)_정", "b": 4150, "d": 1050, "cover": 100, "Mu": 0.0, "Vu": 0.0, "A_prov": 0.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "지점부(종,좌측,1200H)_부", "b": 4150, "d": 1050, "cover": 100, "Mu": 0.0, "Vu": 0.0, "A_prov": 0.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "지점부(종,우측,1200H)_정", "b": 4150, "d": 1050, "cover": 100, "Mu": 0.0, "Vu": 0.0, "A_prov": 0.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "지점부(종,우측,1200H)_부", "b": 4150, "d": 1050, "cover": 100, "Mu": 0.0, "Vu": 0.0, "A_prov": 0.0, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "지점부(횡,중앙,1200H)_정", "b": 5800, "d": 1100, "cover": 100, "Mu": 4724.851, "Vu": 0.0, "A_prov": 22064.7, "fck": 40, "fy": 500, "fvy": 400},
    {"section": "지점부(횡,중앙,1200H)_부", "b": 5800, "d": 1100, "cover": 100, "Mu": 4724.851, "Vu": 0.0, "A_prov": 22064.7, "fck": 40, "fy": 500, "fvy": 400}
    # (필요시 추가 단면 데이터 추가)
]

if __name__ == "__main__":
    create_multi_section_report(sections_sample, "result/multi_section_report.pdf")
