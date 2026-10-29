"""
3단계: 손계산 baseline vs AI(Optuna) 설계 비교

실행 (가상환경 켠 상태에서):
  python examples/step3_compare_baseline.py           seed 3개 x 60회 (약 3분)
  python examples/step3_compare_baseline.py 100       seed 3개 x 100회

결과
  results/step3_comparison.csv     비교표 (엑셀로 열림)
  results/step3_convergence.png    AI 수렴 그래프 (발표용)
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "circuits"))

from buck_baseline import design
from buck_converter_spec import BUCK_SPEC
from optimizer import evaluate, optimize

N_TRIALS = int(sys.argv[1]) if len(sys.argv) > 1 else 60
SEEDS = [0, 1, 2]
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

rows = []


def add_row(label, params, metrics, feasible):
    rows.append({
        "설계": label,
        "L [uH]": round(params["L"] * 1e6, 2),
        "C [uF]": round(params["C"] * 1e6, 1),
        "FSW [kHz]": round(params["FSW"] / 1e3, 1),
        "D": round(params["D"], 4),
        "효율 [%]": round(metrics.get("eff", float("nan")) * 100, 2),
        "평균전압 [V]": round(metrics.get("vavg", float("nan")), 3),
        "최대전압 [V]": round(metrics.get("vmax", float("nan")), 3),
        "리플 [mV]": round(metrics.get("ripple", float("nan")) * 1e3, 1),
        "조건 만족": "O" if feasible else "X",
    })


# 1. 손계산 baseline 두 개
print("=" * 60)
print("1. 손계산 baseline")
print("=" * 60)
baseline_eff = None
for method, label in [("ideal", "사람 A (이상적 공식)"),
                      ("loss_corrected", "사람 B (손실 보정 공식)")]:
    p = design(method)
    _, m, ok = evaluate(BUCK_SPEC, p)
    add_row(label, p, m, ok)
    if method == "loss_corrected":
        baseline_eff = m["eff"]

# 2. AI 최적화 (seed 여러 개 -> 운이 아니라는 걸 보여주기)
print()
print("=" * 60)
print(f"2. AI 최적화 (seed {len(SEEDS)}개 x {N_TRIALS}회)")
print("=" * 60)
curves = {}
for seed in SEEDS:
    best, records = optimize(BUCK_SPEC, n_trials=N_TRIALS, seed=seed,
                             out_csv=OUT / f"step3_trials_seed{seed}.csv", verbose=False)
    curve, cur = [], None
    for r in records:
        if r["feasible"] and (cur is None or r["eff"] > cur):
            cur = r["eff"]
        curve.append(cur)
    curves[seed] = curve
    first_ok = next((i + 1 for i, v in enumerate(curve) if v is not None), None)
    print(f"  seed {seed}: 최고 효율 {best['eff'] * 100:.2f} %  "
          f"(처음 조건 만족: {first_ok}번째 시도)")
    add_row(f"AI (seed {seed})", best, best, True)

# 3. 비교표 출력 + 저장
print()
print("=" * 60)
print("3. 비교 결과")
print("=" * 60)
keys = list(rows[0].keys())
widths = {k: max(len(str(k)), *(len(str(r[k])) for r in rows)) for k in keys}
print("  ".join(str(k).ljust(widths[k]) for k in keys))
for r in rows:
    print("  ".join(str(r[k]).ljust(widths[k]) for k in keys))

with open(OUT / "step3_comparison.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)

ai_effs = [r["효율 [%]"] for r in rows if r["설계"].startswith("AI")]
mean_ai = sum(ai_effs) / len(ai_effs)
print()
print(f"  사람 B 대비 AI 효율 개선: 평균 {mean_ai - baseline_eff * 100:+.2f} %p "
      f"(최소 {min(ai_effs) - baseline_eff * 100:+.2f}, 최대 {max(ai_effs) - baseline_eff * 100:+.2f})")
print(f"  사람 A는 손실을 무시해서 평균전압 조건(4.10 V 이상)을 만족하지 못함")

# 4. 수렴 그래프 (matplotlib 있을 때만)
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("\n  (matplotlib 이 없어서 그래프는 건너뜀: python -m pip install matplotlib)")
    sys.exit(0)

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]

fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

x = list(range(1, N_TRIALS + 1))
for i, seed in enumerate(SEEDS):
    y = [v * 100 if v is not None else float("nan") for v in curves[seed]]
    ax.step(x, y, where="post", color=SERIES[i], lw=2, label=f"AI (seed {seed})")

ax.axhline(baseline_eff * 100, color=INK2, lw=1.5, ls=(0, (5, 4)))
ax.text(N_TRIALS, baseline_eff * 100, f"  Human B {baseline_eff * 100:.2f}%",
        va="center", ha="left", color=INK2, fontsize=9)

ax.set_title("Buck converter: AI best feasible efficiency vs. trial", loc="left",
             color=INK, fontsize=12, pad=12)
ax.set_xlabel("Trial", color=INK2)
ax.set_ylabel("Efficiency (%)", color=INK2)
ax.set_xlim(1, N_TRIALS)
ax.grid(axis="y", color=GRID, lw=0.8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(AXIS)
ax.tick_params(colors=MUTED, labelsize=9)
ax.legend(frameon=False, loc="lower right", fontsize=9, labelcolor=INK2)
fig.text(0.01, 0.01, "Human A (ideal D = Vout/Vin) fails Vavg >= 4.10 V, so it has no feasible point.",
         color=MUTED, fontsize=8)
fig.tight_layout(rect=(0, 0.03, 0.93, 1))
fig.savefig(OUT / "step3_convergence.png", facecolor=SURFACE)
print(f"\n  그래프 저장: results/step3_convergence.png")
