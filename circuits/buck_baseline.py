"""
buck_baseline.py
사람이 교과서 공식으로 손계산하는 buck 컨버터 설계 (AI와 비교할 baseline).

두 가지 baseline
  A. 이상적 공식   : D = Vout / Vin  (손실 무시, 교과서 첫 공식)
  B. 손실 보정 공식 : D = (Vout + Vd) / (Vin - Vsw + Vd)
                     (다이오드 전압강하, 스위치 전압강하 반영. 실무에서 쓰는 방식)

L, C 선정은 둘 다 같은 표준 절차
  - 스위칭 주파수: 200 kHz (소형 컨버터에서 흔히 쓰는 값)
  - 인덕터 리플전류: 출력전류의 40%  (보통 20~40% 범위에서 고름)
      L = (Vin - Vout) * D / (fsw * dI)
  - 출력 리플전압: 목표 30 mV
      dV = dI / (8 * fsw * C) + ESR * dI   ->  C 계산 후 여유 2배
  - 계산값은 실제 살 수 있는 E6 표준값으로 맞춤
"""

import math

# 설계 조건 (buck_converter.cir 과 같은 값)
VIN = 12.0
VOUT_TARGET = 4.15      # 4.10 ~ 4.20 V 범위의 가운데
RLOAD = 4.2
ESR = 0.02              # 출력 커패시터 ESR [ohm]
VD = 0.35               # 쇼트키 다이오드 전압강하 (데이터시트 대략값)
RON = 0.05              # 스위치 온저항 [ohm]

FSW = 200e3
RIPPLE_I_RATIO = 0.40
RIPPLE_V_TARGET = 0.030
C_MARGIN = 2.0

E6 = [1.0, 1.5, 2.2, 3.3, 4.7, 6.8]


def e6_nearest(x):
    """가장 가까운 E6 표준값 (인덕터용)"""
    decade = 10 ** math.floor(math.log10(x))
    cands = [v * decade for v in E6] + [10 * decade]
    return min(cands, key=lambda c: abs(math.log(c / x)))


def e6_round_up(x):
    """x 이상인 가장 작은 E6 표준값 (커패시터용, 여유 쪽으로)"""
    decade = 10 ** math.floor(math.log10(x))
    for v in E6 + [10.0]:
        if v * decade >= x * 0.999:
            return v * decade
    return 10 * decade


def design(method="loss_corrected", verbose=True):
    iout = VOUT_TARGET / RLOAD

    if method == "ideal":
        duty = VOUT_TARGET / VIN
        duty_txt = f"D = Vout/Vin = {VOUT_TARGET}/{VIN}"
    else:
        vsw = iout * RON
        duty = (VOUT_TARGET + VD) / (VIN - vsw + VD)
        duty_txt = (f"D = (Vout+Vd)/(Vin-Vsw+Vd) = ({VOUT_TARGET}+{VD})/"
                    f"({VIN}-{vsw:.3f}+{VD})")

    d_i = RIPPLE_I_RATIO * iout
    l_calc = (VIN - VOUT_TARGET) * duty / (FSW * d_i)
    l_std = e6_nearest(l_calc)
    d_i_real = (VIN - VOUT_TARGET) * duty / (FSW * l_std)   # 표준값 L 기준 실제 리플전류

    dv_cap = RIPPLE_V_TARGET - ESR * d_i_real
    c_calc = d_i_real / (8 * FSW * dv_cap)
    c_std = e6_round_up(c_calc * C_MARGIN)

    if verbose:
        name = "A. 이상적 공식" if method == "ideal" else "B. 손실 보정 공식"
        print(f"--- baseline {name} ---")
        print(f"  Iout = {iout:.3f} A")
        print(f"  {duty_txt} = {duty:.4f}")
        print(f"  dI = {RIPPLE_I_RATIO:.0%} x Iout = {d_i:.3f} A")
        print(f"  L = (Vin-Vout)*D/(fsw*dI) = {l_calc * 1e6:.1f} uH -> 표준값 {l_std * 1e6:.0f} uH")
        print(f"  C = dI/(8*fsw*dVc) = {c_calc * 1e6:.1f} uF -> 여유 x{C_MARGIN:.0f} -> 표준값 {c_std * 1e6:.0f} uF")

    return {"L": l_std, "C": c_std, "FSW": FSW, "D": duty}
