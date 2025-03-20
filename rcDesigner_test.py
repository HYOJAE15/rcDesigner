import numpy as np
import pandas as pd
from fpdf import FPDF

# 단면검토 함수 정의
def section_check(name, fck, fy, b, d, Mu, Vu, As_used, cover, bar_diameter, num_bars):
    Es = 200000  # MPa
    phi_f = 0.85  # 휨 강도감소계수 기본값
    phi_v = 0.80  # 전단 강도감소계수

    # 등가 직사각형 압축블록 깊이 a 산정
    a = As_used * fy / (0.85 * fck * b)
    beta1 = 0.85 if fck <= 28 else max(0.85 - 0.05 * ((fck - 28) / 7), 0.65)
    c = a / beta1

    # 강도감소계수(Φ) 산정
    epsilon_t = 0.003 * (d - c) / c
    phi = 0.85 if epsilon_t >= 0.005 else 0.65 + (epsilon_t - 0.002) * (200 / 3)
    phi_f = min(max(phi_f, phi_f), 0.90)

    # 철근비 검토
    rho_min = max(1.4 / fy, 0.25 * np.sqrt(fck) / fy)
    rho_max = 0.85 * 0.714 * (fck/fy) * (600/(600 + fy))
    rho_use = As_used / (b * d)
    rho_check = "O.K" if rho_max >= rho_use >= rho_min else "N.G"

    # 휨 강도 산정
    Mn = As_used * fy * (d - a / 2) / 1e6  # kN.m
    phiMn = phi_f * Mn
    moment_check = "O.K" if phiMn >= Mu else "N.G"

    # 전단강도 산정
    phiVc = phi_v * (1/6) * np.sqrt(fck) * b * d / 1000  # kN
    shear_check = "O.K" if phiVc >= Vu else "N.G"

    # 철근 간격 검토
    fs = Mu * 1e6 / (As_used * (d - c/3))
    Cc = cover - bar_diameter / 2
    Kcr = 210  # 습윤환경 기준
    Sa = min(375 * (Kcr / fs) - 2.5 * Cc, 300 * (Kcr / fs))
    actual_spacing = 1000 / num_bars
    spacing_check = "O.K" if actual_spacing <= Sa else "N.G"

    return {
        "지점명": sec["name"],
        "Mu(kN.m)": Mu,
        "phiMn(kN.m)": round(phiMn, 2),
        "Vu(kN)": Vu,
        "phiVc(kN)": round(phiVc, 2),
        "철근비검토": rho_use,
        "철근비확인": rho_min <= rho_use <= rho_max,
        "휨검토": moment_check,
        "전단검토": shear_check,
        "간격검토": spacing_check
    }

# 단면 검토 및 결과 저장
results = []
sections = [
    {"name": "좌측단부", "fck":27, "fy":400, "b":1000, "d":720, "Mu":63.28, "Vu":369.40, "As_used":5745.5, "cover":80, "bar_diameter":29, "num_bars":10},
    {"name": "중앙부(지간1)", "fck":27, "fy":400, "b":1000, "d":740, "Mu":1036.81, "Vu":0, "As_used":5745.5, "cover":60, "bar_diameter":29, "num_bars":10},
    {"name": "중간지점1", "fck":27, "fy":400, "b":1000, "d":1020, "Mu":1827.32, "Vu":524.70, "As_used":6424.0, "cover":80, "bar_diameter":29, "num_bars":10},

    ]

results = []
for sec in sections:
    result = section_check(sec["fck"], sec["fy"], sec["b"], sec["d"], sec["Mu"], sec["Vu"],
                           sec["As_used"], sec["cover"], sec["bar_diameter"], sec["num_bars"])
    result["지점명"] = sec["name"]
    results.append(result)

# Excel로 저장
df = pd.DataFrame(results)
df.to_excel("section_check_results.xlsx", index=False)

# PDF 저장 예시
from fpdf import FPDF
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=10)

# 테이블 헤더 생성
headers = results[0].keys()
for header in headers:
    pdf.cell(27, 10, header, 1)
pdf.ln()

# 테이블 데이터 입력
for result in results:
    for value in result.values():
        pdf.cell(27, 10, str(value), 1)
    pdf.ln()

pdf.output("section_check_results.pdf")

# 엑셀 저장
import pandas as pd
pd.DataFrame(results).to_excel("section_check_results.xlsx", index=False)

print("단면검토 결과가 Excel과 PDF로 저장되었습니다.")
