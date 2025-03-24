import math

def calc_effective_depth(h, cover, bar_diameter=22):
    """
    유효깊이 d 계산 (단순 가정: 인장철근 1단 배치, 철근 중심까지 cover + bar_radius)
    실제로는 배근 상세도에 따라 보정필요
    """
    return h - (cover + bar_diameter/2)

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
