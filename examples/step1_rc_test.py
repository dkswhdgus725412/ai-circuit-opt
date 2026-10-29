"""
1단계 확인용 스크립트
Python에서 ngspice를 돌리고 결과를 숫자로 받아오는지 확인한다.

실행: 프로젝트 폴더에서  python examples/step1_rc_test.py
"""

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from spice_runner import run_simulation

TEMPLATE = ROOT / "circuits" / "rc_lowpass.cir"


def theory_fc(R, C):
    return 1 / (2 * math.pi * R * C)


# [테스트 1] 한 번 돌려보기
params = {"R": 1000, "C": 100e-9}
results, _ = run_simulation(TEMPLATE, params)

print("=== 테스트 1: 시뮬레이션 1회 실행 ===")
print(f"파라미터: R = {params['R']} ohm, C = {params['C']} F")
print(f"시뮬레이션 fc = {results['fc']:.1f} Hz")
print(f"이론값     fc = {theory_fc(**params):.1f} Hz")
print(f"10kHz 이득    = {results['gain_10k']:.2f} dB")

# [테스트 2] 값을 바꿔가며 여러 번 돌려보기
# -> 2단계에서는 이 for문 자리에 Optuna가 들어간다
print("\n=== 테스트 2: R을 바꿔가며 반복 실행 ===")
print(f"{'R [ohm]':>10} {'sim fc [Hz]':>14} {'theory fc [Hz]':>16} {'error [%]':>10}")
for R in [470, 1000, 2200, 4700, 10000]:
    p = {"R": R, "C": 100e-9}
    res, _ = run_simulation(TEMPLATE, p)
    th = theory_fc(**p)
    err = abs(res["fc"] - th) / th * 100
    print(f"{R:>10} {res['fc']:>14.1f} {th:>16.1f} {err:>10.2f}")
