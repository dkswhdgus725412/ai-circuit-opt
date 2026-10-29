# AI 기반 회로 자동 설계 최적화

회생제동 기반 배터리-모터 통합 구동 시스템의 컨버터 / 모터 구동회로 설계 파라미터를
ngspice + Optuna (+ LLM)로 자동 최적화하는 프로젝트.

## 진행 단계

- [x] 1단계: Python에서 ngspice 실행하고 측정값 받아오기
- [ ] 2단계: 기본 buck 컨버터로 Optuna 최적화 루프 완성
- [ ] 3단계: baseline(손계산 설계)과 AI 결과 비교
- [ ] 4단계: 팀원 실제 회로(컨버터 / 모터 구동)로 교체
- [ ] 5단계: LLM 레이어 추가 (선택)

## 폴더 구조

```
ai-circuit-opt/
  circuits/          회로 템플릿 (.cir), 바꿀 값은 {{이름}} 으로 표시
  src/
    spice_runner.py  템플릿 채우기 -> ngspice 실행 -> .meas 결과 dict 반환
  examples/          단계별 확인용 스크립트
  results/           실행 결과 저장 (git에는 안 올라감)
```

## 설치

1. Python 3.10 이상
2. ngspice 설치
   - Windows: https://ngspice.sourceforge.io/download.html 에서 받아서 압축 풀고,
     `Spice64/bin` 폴더를 환경변수 PATH에 추가
   - Mac: `brew install ngspice`
   - Ubuntu: `sudo apt install ngspice`
3. 터미널에서 `ngspice --version` 이 나오면 성공
4. `pip install -r requirements.txt`

## 1단계 실행

```
python examples/step1_rc_test.py
```

RC 저역통과 필터의 차단주파수를 시뮬레이션으로 구해서 이론값 1/(2 pi R C)와 비교한다.
0.24% 정도 차이가 나는데, 정확한 차단점 이득은 -3dB가 아니라 -3.01dB 이기 때문이라 정상.

## 회로 템플릿 작성 규칙 (팀 공통)

새 회로를 추가할 때 아래 규칙을 지키면 최적화 엔진을 공유할 수 있다.

1. 바꿀 값은 `{{이름}}` 으로 표시 (예: `L1 sw out {{L}}`)
2. batch 모드라서 `.save v(노드)` 로 측정에 쓰는 노드를 꼭 저장
3. 평가에 쓸 값은 전부 `.meas` 로 뽑기 (이름은 소문자로 받아짐)
4. 파일 맨 위 주석에 변수 목록과 단위 적어두기

## 사용 예

```python
from spice_runner import run_simulation

results, log = run_simulation("circuits/rc_lowpass.cir", {"R": 1000, "C": 100e-9})
print(results)   # {'fc': 1587.8, 'gain_10k': -16.07}
```

측정이 실패한 값은 dict에 빠져 있으므로, 최적화할 때는 "필요한 키가 없으면 탈락"으로 처리한다.
