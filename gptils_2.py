import math

##################################################################
# 휨 관련
##################################################################

# def required_rebar_area(Mu, b, d, fck, fy, phi_s=0.90, phi_c=0.65, alpha=0.8, beta=0.4):
#     """
#     단철근 직사형 단면 휨설계에서 정확한 필요철근량(As)을 구하는 함수

#     Mu  : 설계모멘트 (kN·m)
#     b   : 단면폭 (mm)
#     d   : 유효깊이 (mm)
#     fck : 콘크리트 압축강도 (MPa)
#     fy  : 철근 항복강도 (MPa)
#     phi : 강도저감계수 (일반적으로 0.90)
#     """
#     Mu_Nmm = Mu * 1e6  # kN·m → N·mm 변환

#     # 이차방정식 형태: K·As² - B·As + C = 0
#     K = ((fy**2)*beta*phi_s) / (alpha*phi_c*(0.85*fck)*b)
#     B = fy * d
#     C = Mu_Nmm / phi_s

#     discriminant = B**2 - 4 * K * C
#     if discriminant < 0:
#         return None  # 해 없음

#     As1 = (B + math.sqrt(discriminant)) / (2 * K)
#     As2 = (B - math.sqrt(discriminant)) / (2 * K)

#     As_req = min(As1, As2)
#     if As_req <= 0:
#         return None
#     return As_req

def required_rebar_area(Mu, b, d, fck, fy, phi=0.90):
    """필요철근량 산정 (이차방정식)"""
    Mu_Nmm = Mu * 1e6
    K = (fy**2)/(2*0.85*fck*b)
    B = fy*d
    C = Mu_Nmm/phi
    disc = B**2 - 4*K*C
    if disc<0: return None
    As1 = (B+math.sqrt(disc))/(2*K)
    As2 = (B-math.sqrt(disc))/(2*K)
    As_req = min(As1, As2)
    return As_req if (As_req>0) else None

def calc_min_max_rebar(b, d, fck, fy, As_req=None, As_use=None):
    """최소·최대철근량 계산"""
    As_min_a = 0.25*(fck**0.5)/fy*b*d
    As_min_b = (1.4/fy)*b*d
    As_min_c = (4.0/3.0)*As_req if As_req else 0.0
    candidates = [As_min_a, As_min_b, As_min_c]
    if As_use:
        filtered = [val for val in candidates if val<=As_use]
    else:
        filtered = candidates
    if not filtered:
        As_min=0.0
    else:
        As_min=max(filtered)
    As_max=0.04*b*d
    return As_min,As_max

def check_neutral_axis_depth(As_use,b,d,fck,fy,phi_c=0.65,phi_s=0.90):
    alpha=0.80
    numerator=phi_s*As_use*fy
    denominator=alpha*phi_c*0.85*fck*b
    c=numerator/denominator
    cmax=0.4*d
    return c, cmax, (c<=cmax)

def compute_tensile_strain(d,c,eps_cu=0.0033):
    eps_s=(d-c)/c*eps_cu
    return eps_s

def calculate_design_flexural_strength(As_use,b,d,c,fck,fy,phi=0.90,beta=0.4):
    """Mn, phiMn 산정"""
    a=(As_use*fy)/(0.85*fck*b)
    c_nom=a/beta
    Mn=As_use*fy*(d-beta*c_nom)
    Mn_kNm=Mn/1e6
    phi_Mn=phi*Mn_kNm
    return Mn_kNm,phi_Mn

def shear_check(Vu,b,d,fck,phi_c=0.65):
    """전단강도"""
    k=min(1+math.sqrt(200/d),2)
    Vcd=0.85*phi_c*k*(0.17*(fck**(1/3)))*b*d
    Vcd_min=0.4*phi_c*(0.63*math.sqrt(fck))*b*d
    pass_shear=(Vcd>=Vu*1e3)
    return Vcd,Vcd_min,pass_shear

def min_shear_rebar(Av_use,s,b,fck,fvy):
    pv_min=(0.08*math.sqrt(fck))/fvy
    pv_use=Av_use/(s*b)
    return pv_min,pv_use,(pv_use>=pv_min)

def shear_spacing_check(d,theta=90):
    Smax=min(0.75*d*(1+1/math.tan(math.radians(theta))),600)
    return Smax

def additional_tension(Mn_kNm,Mu,Vu,d,theta=45,alpha=90):
    z=0.9*d
    delta_Tr=(Mn_kNm-Mu)/z  # kN
    delta_T=0.5*Vu*(1/math.tan(math.radians(theta))
                   -1/math.tan(math.radians(alpha)))
    is_ok=(delta_Tr>=delta_T)
    return delta_Tr, delta_T, is_ok

def serviceability_check(Mu,b,h,fck):
    Z=b*h**2/6
    ft=Mu*1e6/Z
    fct=0.23*(fck**(2/3))
    pass_crack=(ft<=fct)
    return ft,fct,pass_crack
