"""
optimizer.py
CircuitSpec 하나를 받아서 Optuna로 자동 최적화하는 공통 엔진.

흐름 (trial 1번):
  Optuna가 변수값 제안 -> run_simulation() -> 측정값
  -> 제약조건 검사 -> 점수 계산 -> Optuna에 점수 보고 -> 다음 값 제안

점수 규칙
  - 시뮬 실패 / 측정값 없음     : 매우 낮은 점수 (FAIL_SCORE)
  - 제약조건 위반              : 목표값 - (1 + 10 x 위반량)  -> 만족하는 설계보다 항상 낮게
  - 제약조건 모두 만족          : 목표값 그대로 (minimize면 부호 반대)
"""

import csv
import time
from pathlib import Path

import optuna

from spice_runner import run_simulation

FAIL_SCORE = -1e6
PENALTY_WEIGHT = 10.0


def evaluate(spec, values):
    """변수값 하나에 대해 시뮬 -> (점수, 측정값, 제약 만족 여부)"""
    try:
        metrics, _ = run_simulation(spec.template, values, timeout=120)
    except Exception:
        return FAIL_SCORE, {}, False

    if any(m not in metrics for m in spec.required_metrics()):
        return FAIL_SCORE, metrics, False

    obj = metrics[spec.objective]
    score = obj if spec.direction == "maximize" else -obj

    total_violation = sum(c.violation(metrics[c.metric]) for c in spec.constraints)
    feasible = total_violation == 0
    if not feasible:
        score -= 1.0 + PENALTY_WEIGHT * total_violation
    return score, metrics, feasible


def optimize(spec, n_trials=60, seed=0, out_csv=None, verbose=True):
    """
    spec 회로를 n_trials 번 시도해서 최적화.
    반환값: 제약을 만족한 trial 중 가장 좋은 것 (dict) / 없으면 None
    """
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)

    records = []
    best = None
    t0 = time.time()

    def objective(trial):
        nonlocal best
        values = {
            p.name: trial.suggest_float(p.name, p.low, p.high, log=p.log)
            for p in spec.params
        }
        score, metrics, feasible = evaluate(spec, values)

        rec = {"trial": trial.number, **values, **metrics,
               "feasible": feasible, "score": score}
        records.append(rec)

        if feasible and (best is None or score > best["score"]):
            best = rec
            if verbose:
                print(f"  [trial {trial.number:3d}] 새 최고 기록  "
                      f"{spec.objective} = {metrics[spec.objective]:.4f}")
        return score

    if verbose:
        print(f"[{spec.name}] 최적화 시작: {n_trials} trials")
    study.optimize(objective, n_trials=n_trials)

    if verbose:
        n_ok = sum(r["feasible"] for r in records)
        print(f"[{spec.name}] 완료: {time.time() - t0:.0f}초, "
              f"제약 만족 {n_ok}/{len(records)}")

    if out_csv:
        save_csv(records, out_csv)
    return best, records


def save_csv(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = []
    for r in records:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(records)
