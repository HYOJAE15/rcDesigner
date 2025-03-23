import math
import pandas as pd
from docx import Document
from docx.shared import Inches
# 필요시 from openpyxl import load_workbook 등 다른 라이브러리도 활용 가능

# ---------------------------
# 1) 철근콘크리트 휨·전단 검토에 필요한 간단 함수들 (단순화 예시)
# ---------------------------

# def calc_effective_depth(h, cover, bar_diameter=22):
#     """
#     유효깊이 d 계산 (단순 가정: 인장철근 1단 배치, 철근 중심까지 cover + bar_radius)
#     실제로는 배근 상세도에 따라 보정필요
#     """
#     return h - (cover + bar_diameter/2)

def solve_rebar_area_for_flexure(Mu, b, d, fck, fy, phi_c=0.65, phi_s=0.90):
    """
    단순 직사형 단면(단철근) 휨설계에서 필요한 철근량 As를
    2차방정식을 통해 구하는 예시 (KDS/KCI 식과 유사한 방식)

    Mu = As * φs * fy * (d - β*c)
    c  = As * φs * fy / (α*φc*0.85*fck*b)
    를 결합 -> 2차 방정식 형태로 근사해
    """
    alpha = 0.80
    beta  = 0.40
    # 편의를 위해 단위계: Mu[kN·m] => N·mm로 변환
    Mu_Nmm = Mu * 1e6

    # 2차방정식 계수 A·B·C 구하기
    #   A = (beta * (phi_s^2) * (fy^2)) / (alpha * phi_c * 0.85 * fck * b)
    A = (beta * (phi_s**2) * (fy**2)) / (alpha * phi_c * 0.85 * fck * b)
    #   B = - phi_s*fy*d
    B = - (phi_s * fy * d)
    #   C = Mu_Nmm
    C = Mu_Nmm

    # 근의 공식을 이용한 해
    # A * As^2 + B * As + C = 0  → 해가 음수면 안 되므로 양의 해만 사용
    discriminant = B**2 - 4*A*C
    if discriminant <= 0:
        # 이 경우 Mu가 너무 커서 단순 공식으로는 해석불가 → 더 두꺼운 단면 혹은 추가 검사 등 필요
        return None

    As1 = (-B + math.sqrt(discriminant)) / (2*A)
    As2 = (-B - math.sqrt(discriminant)) / (2*A)
    # 양의 해를 반환
    As_req = max(As1, As2)
    return As_req

def calc_shear_check(Vu, b, d, fck, fy, phi_c=0.65, phi_s=0.90):
    """
    전단강도(단순 무근전단 or 최소 전단철근 가정) 검토 예시
    KDS 14 또는 KCI 식 등에서 Vc, Vs를 구해보는 단순화 버전
    """
    # 단순 무근전단강도 Vc (일부 식만 예시)
    # Vc = 0.53 * sqrt(fck) * b * d (MPa => N/mm^2 등등)
    # 여기서는 표준식이 아닌 예시로만 제시
    Vc = 0.53 * (fck**0.5) * b * d * 1e-3  # kN 단위
    if Vu <= Vc:
        return True, Vc, 0.0  # 전단철근 불필요, (Vc, Vs)
    else:
        # 전단철근이 필요한 경우 Vs로 보강 가능하다고 보고 OK 처리(단순 예시).
        # 실제는 스터럽 배치(간격, 각도), 최대 전단강도(Vmax) 등을 추가 검토해야 함
        # 여기서는 Vs를 Vu - Vc 정도로 계산
        Vs = Vu - Vc
        return True, Vc, Vs

# ---------------------------
# 2) 메인 함수
# ---------------------------

def generate_rc_report(excel_path, output_docx='RC_Report.docx'):
    """
    1. 엑셀 파일(설계 입력)을 읽는다
    2. 각 부재별 휨·전단 검토를 수행한다
    3. docx 형태의 보고서를 생성한다
    """
    # (1) 엑셀 데이터 불러오기
    df = pd.read_excel(excel_path, sheet_name='SectionData')

    # 보고서(docx) 문서 생성
    doc = Document()
    doc.add_heading('철근콘크리트 단면검토 자동보고서', level=1)
    doc.add_paragraph('본 문서는 Python 스크립트를 통해 생성된 자동화 예시 보고서입니다.')
    doc.add_paragraph('설계기준(예: KDS 14 20** 또는 KCI 등)에 따라 식과 계수는 적절히 조정 필요합니다.')

    # (2) 각 행(부재)에 대해 반복 계산
    for idx, row in df.iterrows():
        member_id = row['MemberID']
        b = row['b(mm)']
        h = row['h(mm)']
        d = row['d(mm)']
        cover = row['cover(mm)']
        fck = row['fck(MPa)']
        fy  = row['fy(MPa)']
        Vu  = row['Vu(kN)']
        Mu  = row['Mu(kN·m)']
        
        # 유효깊이(d) 계산(철근 지름 가정)
        # 실제는 row에 '철근직경', '배근층 수' 등의 추가 정보가 있으면 더 정교하게 계산해야 함
        # d = calc_effective_depth(h, cover, bar_diameter=22.0)
        
        # (a) 휨 검토
        As_required = solve_rebar_area_for_flexure(Mu, b, d, fck, fy)
        # 사용 철근량(가정). 여기서는 예시로 “필요량보다 15% 많은 값”이라고 가정
        # 실제는 사용자가 별도 셀에 입력하거나, 철근 호칭 지름·EA 조합으로 산출해야 함
        if As_required is None:
            flexure_ok = False
            As_use = None
            ratio_flex = 999  # 또는 Fail
        else:
            As_use = As_required * 1.15  
            ratio_flex = As_use / As_required  # 단순비
            
            flexure_ok = (ratio_flex >= 1.0)  # 사용철근 ≥ 요구철근인지

        # (b) 전단 검토
        shear_ok, Vc, Vs = calc_shear_check(Vu, b, d, fck, fy)
        
        # (c) 사용성(균열폭 등) 검토
        # 예시에서는 간단히 “비균열 가정 시 ft 계산해보고, ft > fct일 때 균열로 판단”
        # → 균열이면 As_min 이상인지 확인하는 정도만 시연
        # 실제는 KDS 24 14 21 4.2.3.4 식 등에 따라 균열폭 Wk 계산, 한계폭과 비교가 필요
        Ec = 200000  # 단위 MPa, 단순 가정
        fct = 0.23 * (fck**(2/3))  # (예시) 장기값 고려 안 함
        # 비균열 가정시 극단섬유인장응력 ft ~ M/Z 로 가정
        # Z ~ b*h^2/6 (직사단면 기준), 단순예시
        Z = b*(h**2)/6.0
        ft = (Mu*1e6)/Z  # [N/mm^2] = MPa
        crack_check = (ft <= fct)
        
        # 보고서에 기재할 문단 생성
        doc.add_heading(f'부재 ID: {member_id}', level=2)

        para = doc.add_paragraph()
        para.add_run(f"단면치수: 폭 b = {b} mm, 높이 h = {h} mm, 유효깊이 d ≈ {d:.1f} mm\n").bold=True
        para.add_run(f"콘크리트강도 fck = {fck} MPa, 철근강도 fy = {fy} MPa\n")
        para.add_run(f"설계 전단력 Vu = {Vu:.3f} kN, 설계 휨모멘트 Mu = {Mu:.3f} kN·m\n")

        # 휨결과
        if As_required is None:
            para.add_run("[휨검토] 요구철근량 계산 불가 → 단면이 너무 작은 것으로 추정\n").italic = True
        else:
            para.add_run(f"[휨검토] 요구철근량 As_req = {As_required:.1f} mm²\n")
            para.add_run(f"            사용철근량 As_use = {As_use:.1f} mm² → 사용률 = {ratio_flex*100:.1f}%\n")
            para.add_run(f"            휨검토 결과: {'OK' if flexure_ok else 'NG'}\n")

        # 전단결과
        para.add_run(f"[전단검토] Vc(무근전단강도 추정) = {Vc:.1f} kN, Vs(필요 전단보강) = {Vs:.1f} kN\n")
        para.add_run(f"            전단검토 결과: {'OK' if shear_ok else 'NG'}\n")
        
        # 균열여부/사용성
        if crack_check:
            para.add_run(f"[사용성/균열] 비균열 상태로 추정 (ft={ft:.2f} MPa ≤ fct={fct:.2f} MPa)\n")
        else:
            para.add_run(f"[사용성/균열] 균열 발생 가능 (ft={ft:.2f} MPa > fct={fct:.2f} MPa)\n")
            para.add_run(" → KDS 24 14 21 4.2.3.4 식 등에 따른 균열폭 계산 및 최소철근량 확인 필요\n")
        
        para.add_run("--------------------------------------------------------------------------------\n")

    # (3) 최종 docx 파일 저장
    doc.save(output_docx)
    print(f"보고서 생성 완료: {output_docx}")


# ---------------------------
# 3) 실제 스크립트 실행 (직접 호출 예시)
# ---------------------------

if __name__ == "__main__":
    # 준비된 엑셀 파일 경로
    input_excel = "section_input.xlsx"  
    output_file = "RC_Design_Report.docx"

    generate_rc_report(input_excel, output_docx=output_file)
    print("모든 계산 완료!")
