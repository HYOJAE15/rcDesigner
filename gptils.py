import math

def required_rebar_area(Mu, b, d, fck, fy, phi=0.90):
    """
    단철근 직사형 단면 휨설계에서 정확한 필요철근량(As)을 구하는 함수

    Mu  : 설계모멘트 (kN·m)
    b   : 단면폭 (mm)
    d   : 유효깊이 (mm)
    fck : 콘크리트 압축강도 (MPa)
    fy  : 철근 항복강도 (MPa)
    phi : 강도저감계수 (일반적으로 0.90)
    """
    Mu_Nmm = Mu * 1e6  # kN·m → N·mm 변환

    # 등가 압축블록 깊이(a) = As·fy / (0.85·fck·b)
    # Mn = As·fy·(d - a/2)
    # 설계 조건: Mu = phi * Mn
    # → Mu/phi = As·fy·(d - (As·fy) / (2·0.85·fck·b))

    # 이차방정식 형태: K·As² - B·As + C = 0
    K = (fy**2) / (2 * 0.85 * fck * b)
    B = fy * d
    C = Mu_Nmm / phi

    discriminant = B**2 - 4 * K * C
    if discriminant < 0:
        raise ValueError("해가 존재하지 않음: 단면이 부족하거나 입력값 오류")

    # 근의 공식 적용
    As1 = (B + math.sqrt(discriminant)) / (2 * K)
    As2 = (B - math.sqrt(discriminant)) / (2 * K)

    # 양수의 근만 선택
    As_req = min(As1, As2)
    if As_req <= 0:
        raise ValueError("올바른 해가 없음: 계산식 또는 입력값 확인 필요")

    return As_req


def calc_min_max_rebar(b, d, fck, fy,
                       As_req=None, As_use=None):
    """
    최소·최대 철근량(As_min, As_max)을 구하는 예시.
    - (a) 0.25*√fck/fy * b*d
    - (b) (1.4/fy)*b*d
    - (c) (4/3)*As_req (필요철근량의 1.33배)
      이 중 최댓값을 As_min으로(단, As_use보다 큰 값은 제외).

    - As_max = 0.04 * b * d
    """
    # (a)
    As_min_a = 0.25 * (fck**0.5) / fy * b * d
    # (b)
    As_min_b = (1.4 / fy) * b * d
    # (c)
    if As_req is not None:
        As_min_c = (4.0/3.0) * As_req
    else:
        As_min_c = 0.0

    candidates = [As_min_a, As_min_b, As_min_c]

    if As_use is not None:
        filtered = [val for val in candidates if val <= As_use]
    else:
        filtered = candidates

    # 필터링 후 아무것도 안남으면 0으로 처리
    if not filtered:
        As_min = 0.0
    else:
        As_min = max(filtered)

    # 최대철근
    As_max = 0.04 * b * d
    return As_min, As_max


def check_neutral_axis_depth(As_use, b, d, fck, fy,
                             phi_c=0.65, phi_s=0.90):
    """
    배근된 인장철근량(As_use)에 대해
    중립축 깊이 c와 cmax(=0.4*d 가정) 비교
    """
    alpha = 0.80
    # c = (φs * As_use * fy) / (α * φc * 0.85 * fck * b)
    numerator   = phi_s * As_use * fy
    denominator = alpha * phi_c * 0.85 * fck * b
    c = numerator / denominator

    cmax = 0.4 * d
    c_ok = (c <= cmax)
    return c, cmax, c_ok


def compute_tensile_strain(d, c, eps_cu=0.0033):
    """
    인장철근 변형률: εs = ((d-c)/c)*εcu
    (단철근 가정)
    """
    eps_s = (d - c) / c * eps_cu
    return eps_s


def calc_shear_check(Vu, b, d, fck, fy,
                     phi_c=0.65, phi_s=0.90):
    """
    (단순 예시) 전단강도 Vc = 0.53 * √fck * b * d * 1e-3 (kN)
    Vu ≤ Vc 면 무근전단OK, 그렇지 않으면 Vs=Vu-Vc만큼 보강한다 가정.
    """
    Vc = 0.53 * (fck**0.5) * b * d * 1e-3  # kN
    if Vu <= Vc:
        return True, Vc, 0.0
    else:
        Vs = Vu - Vc
        return True, Vc, Vs
    
def calculate_design_flexural_strength(As, b, d, c, fck, fy, phi=0.90, beta=0.4):
    """
    필요철근량(As)을 이용한 설계 휨강도(ϕMn) 산정 과정
    """
    # 등가 압축블록 깊이(a) 계산
    a = (As * fy) / (0.85 * fck * b)

    # 중립축 깊이(c) 계산 (β1 = 0.85 일반적 가정)
    # beta1 = 0.85
    c = a / beta

    # 공칭 휨강도(Mn) 계산 (N·mm)
    Mn = As * fy * (d - beta*c)
    # print(As, fy, d, beta, c)

    # 단위 환산(N·mm → kN·m)
    Mn_kNm = Mn / 1e6

    # 설계 휨강도(ϕMn) 계산
    phi_Mn = phi * Mn_kNm

    return Mn, phi_Mn

def shear_check(Vu, b, d, fck, phi_c=0.65):
    k = min(1 + math.sqrt(200 / d), 2)
    Vcd = 0.85 * phi_c * k * (0.17 * (fck**(1/3))) * b * d
    Vcd_min = 0.4 * phi_c * (0.63 * math.sqrt(fck)) * b * d

    return Vcd, Vcd_min, Vcd >= Vu * 1e3

def min_shear_rebar(Av_use, s, b, fck, fvy):
    pv_min = (0.08 * math.sqrt(fck)) / fvy
    pv_use = Av_use / (s * b)
    return pv_min, pv_use, pv_use >= pv_min

def shear_spacing_check(d, theta=90):
    Smax = min(0.75 * d * (1 + (1 / math.tan(math.radians(theta)))), 600)
    return Smax

def additional_tension(Mr, Mu, Vu, d, theta=45, alpha=90):
    z = 0.9 * d
    delta_Tr = (Mr - Mu) / z
    delta_T = 0.5 * Vu * (1 / math.tan(math.radians(theta)) - 1 / math.tan(math.radians(alpha)))
    return delta_Tr, delta_T, delta_Tr >= delta_T

def serviceability_check(Mu, b, h, fck):
    Z = b * h**2 / 6
    ft = Mu * 1e6 / Z
    fct = 0.23 * fck**(2/3)
    return ft, fct, ft <= fct
