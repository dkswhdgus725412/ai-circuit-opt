"""
buck_converter.cir 의 회로 정의.
(새 회로를 추가할 때 이 파일을 복사해서 고치면 됨)
"""

from pathlib import Path

from circuit_spec import CircuitSpec, Constraint, Param

HERE = Path(__file__).resolve().parent

BUCK_SPEC = CircuitSpec(
    name="buck_converter",
    template=HERE / "buck_converter.cir",

    # AI가 바꿔볼 변수와 범위
    params=[
        Param("L",   4.7e-6, 47e-6,  log=True, unit="H"),
        Param("C",   10e-6,  220e-6, log=True, unit="F"),
        Param("FSW", 50e3,   500e3,  log=True, unit="Hz"),
        Param("D",   0.30,   0.45,             unit="-"),
    ],

    # 목표: 효율 최대
    objective="eff",
    direction="maximize",

    # 반드시 지킬 조건 (임시 스펙 기준)
    constraints=[
        Constraint("vmax",   max=4.20),   # 배터리 최대 충전전압 (하드 리밋)
        Constraint("vavg",   min=4.10),   # 충전이 되려면 이 정도는 나와야 함
        Constraint("ripple", max=0.030),  # 출력 리플 30mV 이하
    ],
)
