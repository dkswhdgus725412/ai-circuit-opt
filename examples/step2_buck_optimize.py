"""
2단계: buck 컨버터를 Optuna로 자동 최적화

실행 (가상환경 켠 상태에서):
  python examples/step2_buck_optimize.py            기본 60회
  python examples/step2_buck_optimize.py 150        150회

결과 전체는 results/buck_trials.csv 에 저장됨 (엑셀로 열림)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "circuits"))

from buck_converter_spec import BUCK_SPEC
from optimizer import optimize

n_trials = int(sys.argv[1]) if len(sys.argv) > 1 else 60

best, records = optimize(
    BUCK_SPEC,
    n_trials=n_trials,
    seed=0,
    out_csv=ROOT / "results" / "buck_trials.csv",
)

print()
if best is None:
    print("제약조건을 만족하는 설계를 못 찾음. trial 수를 늘리거나 범위를 확인할 것.")
    sys.exit(1)

print("=== 최적 설계 ===")
print(f"  L   = {best['L'] * 1e6:7.2f} uH")
print(f"  C   = {best['C'] * 1e6:7.1f} uF")
print(f"  FSW = {best['FSW'] / 1e3:7.1f} kHz")
print(f"  D   = {best['D']:7.4f}")
print("=== 성능 ===")
print(f"  효율     = {best['eff'] * 100:6.2f} %")
print(f"  평균전압 = {best['vavg']:6.3f} V   (기준 4.10 V 이상)")
print(f"  최대전압 = {best['vmax']:6.3f} V   (한계 4.20 V 이하)")
print(f"  리플     = {best['ripple'] * 1e3:6.1f} mV  (한계 30 mV 이하)")

# 진행에 따라 최고 기록이 어떻게 좋아졌는지 (발표 그래프용 데이터)
print("\n=== 진행 상황 (그 시점까지의 최고 효율) ===")
best_so_far = None
for r in records:
    if r["feasible"] and (best_so_far is None or r["eff"] > best_so_far):
        best_so_far = r["eff"]
    if (r["trial"] + 1) % 10 == 0:
        s = f"{best_so_far * 100:.2f} %" if best_so_far else "아직 없음"
        print(f"  trial {r['trial'] + 1:4d}: {s}")
