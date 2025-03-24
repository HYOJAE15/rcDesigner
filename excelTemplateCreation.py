import pandas as pd

def create_excel_template(template_path="section_input_template.xlsx"):
    """
    RC 단면 설계에 필요한 입력값 컬럼을 포함한 엑셀 템플릿을 생성한다.
    - template_path: 생성할 엑셀 파일 이름(경로)
    """

    # 엑셀에 들어갈 컬럼
    columns = [
        "MemberID",   # 부재 식별자(이름)
        "b(mm)",      # 부재 폭
        "h(mm)",      # 부재 전체높이
        "d(mm)",      # 철근 유효깊이
        "cover(mm)",  # 피복 두께
        "fck(MPa)",   # 콘크리트 압축강도
        "fy(MPa)",    # 철근 항복강도
        "Vu(kN)",     # 설계 전단력
        "Mu(kN·m)",   # 설계 휨모멘트
        
        # 필요하면 추가
        # "barDiameter(mm)",  # 주인장철근 지름
        # "nRebar",           # 철근 개수
        # "StirrupSpacing(mm)", # 전단철근 간격
        # ...
    ]

    # 사용자가 직접 입력
    ### [""MemberID", "b(mm)", "h(mm)", "d(mm)", "cover(mm)", "fck(MPa)", "fy(MPa)", "Vu(kN)", "Mu(kN·m)"]
    data = [
        ["슬래브_종방향_정", 1000, 350, 250, 100, 40, 500, 167.204, 242.015],
        ["슬래브_횡방향_정", 1000, 350, 250, 100, 40, 500, 152.166, 206.159],
        # 필요시 더 많은 예시행 추가 가능
    ]

    # 판다스 DataFrame 생성
    df = pd.DataFrame(data, columns=columns)

    # 엑셀파일로 내보내기
    with pd.ExcelWriter(template_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="SectionData", index=False)

    print(f"엑셀 템플릿 생성 완료: {template_path}")

# -------------------------
# 직접 실행 예시
# -------------------------
if __name__ == "__main__":
    create_excel_template()
