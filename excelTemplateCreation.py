import pandas as pd

"""
검토하고자 하는 단면의 제원을 입력하세요.
    "section": ["슬래브_종방향_정", "일반보(종방향)_부", "지점부(횡,중앙,1200H)_정"],
    "b (mm)": [1000, 1000, 5800],
    "d (mm)": [250, 250, 1100],
    "cover (mm)": [100, 100, 100],
    "Mu (kN·m)": [242.015, 152.166, 4724.851],
    "Vu (kN)": [167.204, 206.159, 0.0],
    "A_prov (mm²)": [3096.8, 2292.0, 22064.7],
    "fck (MPa)": [40, 40, 40],
    "fy (MPa)": [500, 500, 500],
    "fvy (MPa)": [400, 400, 400]
"""

template_data = {
    "section": ["슬래브_종방향_정", "일반보(종방향)_부", "지점부(횡,중앙,1200H)_정"],
    "b (mm)": [1000, 1000, 5800],
    "d (mm)": [250, 250, 1100],
    "cover (mm)": [100, 100, 100],
    "Mu (kN·m)": [242.015, 152.166, 4724.851],
    "Vu (kN)": [167.204, 206.159, 0.0],
    "A_prov (mm²)": [3096.8, 2292.0, 22064.7],
    "fck (MPa)": [40, 40, 40],
    "fy (MPa)": [500, 500, 500],
    "fvy (MPa)": [400, 400, 400]
}

df_template = pd.DataFrame(template_data)
df_template.to_excel("section_data_template.xlsx", index=False)

print("엑셀 양식 파일(section_data_template.xlsx)이 생성되었습니다.")
