import pandas as pd

sections = {
    "슬래브": [
        {"section": "슬래브_종방향_정", "b (mm)": 1000, "H (mm)": 350, "d (mm)": 250, "cover (mm)": 100, "Mu (kN·m)": 242.015, "Vu (kN)": 167.204, "A_prov (mm²)": 3096.8, "fck (MPa)": 40, "fy (MPa)": 500, "fvy (MPa)": 400},
        {"section": "슬래브_횡방향_정", "b (mm)": 1200, "H (mm)": 600, "d (mm)": 500, "cover (mm)": 100, "Mu (kN·m)": 500.0, "Vu (kN)": 250.0, "A_prov (mm²)": 6500.0, "fck (MPa)": 40, "fy (MPa)": 500, "fvy (MPa)": 400},
    ]
}

with pd.ExcelWriter("section_data_template.xlsx", engine="openpyxl") as writer:
    for sheet_name, data in sections.items():
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print("엑셀 양식(section_data_template.xlsx)이 생성되었습니다.")
