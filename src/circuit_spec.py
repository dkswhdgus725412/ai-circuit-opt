"""
circuit_spec.py
회로 하나를 최적화 엔진에 넘기기 위한 '회로 정의' 형식 (팀 공통).

회로 하나 = 템플릿 파일 + 변수 범위 + 제약조건 + 최적화 목표

컨버터 담당, 모터 담당 모두 이 형식으로 자기 회로를 정의하면
optimizer.py 하나를 그대로 같이 쓸 수 있다.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Param:
    """AI가 바꿔볼 설계 변수 하나"""
    name: str            # 템플릿의 {{이름}} 과 같아야 함
    low: float
    high: float
    log: bool = False    # 값 범위가 몇 배씩 차이나면(L, C, 주파수) True 추천
    unit: str = ""


@dataclass
class Constraint:
    """반드시 지켜야 하는 조건 (안전 한계 등). min/max 중 필요한 것만 쓰면 됨"""
    metric: str                      # .meas 이름
    min: Optional[float] = None
    max: Optional[float] = None

    def violation(self, value):
        """얼마나 넘었는지 (0이면 만족). 크기 비교가 되도록 상대값으로 계산"""
        v = 0.0
        if self.min is not None and value < self.min:
            v += (self.min - value) / max(abs(self.min), 1e-12)
        if self.max is not None and value > self.max:
            v += (value - self.max) / max(abs(self.max), 1e-12)
        return v


@dataclass
class CircuitSpec:
    name: str
    template: Path
    params: list
    objective: str                   # 최적화할 .meas 이름
    direction: str = "maximize"      # "maximize" 또는 "minimize"
    constraints: list = field(default_factory=list)

    def required_metrics(self):
        names = {self.objective} | {c.metric for c in self.constraints}
        return sorted(names)
