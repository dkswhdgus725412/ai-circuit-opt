# AI 기반 회로 자동 설계 최적화

회생제동 기반 배터리-모터 통합 구동 시스템의 컨버터 / 모터 구동회로 설계 파라미터를
ngspice + Optuna (+ LLM)로 자동 최적화하는 프로젝트.

## 진행 단계

- [x] 1단계: Python에서 ngspice 실행하고 측정값 받아오기
- [x] 2단계: 기본 buck 컨버터로 Optuna 최적화 루프 완성
- [ ] 3단계: baseline(손계산 설계)과 AI 결과 비교
- [ ] 4단계: 팀원 실제 회로(컨버터 / 모터 구동)로 교체
- [ ] 5단계: LLM 레이어 추가 (선택)

## 폴더 구조

```
ai-circuit-opt/
  circuits/
    rc_lowpass.cir            1단계 테스트 회로
    buck_converter.cir        2단계 buck 컨버터 템플릿
    buck_converter_spec.py    buck 회로 정의 (변수 범위, 제약, 목표)
  src/
    spice_runner.py           템플릿 채우기 -> ngspice 실행 -> .meas 결과 dict
    circuit_spec.py           회로 정의 형식 (팀 공통)
    optimizer.py              Optuna 최적화 엔진 (팀 공통)
  examples/                   단계별 실행 스크립트
  results/                    실행 결과 CSV (git에는 안 올라감)
```

## 설치

### 1. ngspice
- Windows: https://ngspice.sourceforge.io/download.html 에서 받아서 압축을 풀고
  `Spice64` 폴더를 `C:\Spice64` 에 둔다.
  - `C:\Spice64` 에 두면 PATH 등록을 안 해도 코드가 자동으로 찾는다.
  - 다른 곳에 뒀다면 PATH에 `...\Spice64\bin` 을 추가하거나,
    환경변수 `NGSPICE_PATH` 에 `ngspice_con.exe` 전체 경로를 넣는다.
  - ngspice.exe는 창을 띄우는 GUI 버전이라 코드는 ngspice_con.exe를 쓴다.
- Mac: `brew install ngspice`
- Ubuntu: `sudo apt install ngspice`

확인: `C:\Spice64\bin\ngspice_con.exe --version` 에서 버전이 나오면 성공.

### 2. Python 3.13 + 가상환경 (중요)

Python 3.15는 optuna가 쓰는 PyYAML 설치가 실패하므로 **3.13** 으로 맞춘다.

```
py install 3.13
cd 프로젝트폴더
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

- 줄 앞에 `(.venv)` 가 붙으면 가상환경이 켜진 상태.
- 터미널을 새로 열 때마다 `.venv\Scripts\activate` 부터 실행.
- `python --version` 에서 숫자 없이 "Python" 만 나오면 Windows 기본 바로가기(가짜)이므로
  python.org 에서 Python을 설치하거나 `py` 명령을 쓴다.

## 1단계 실행

```
python examples\step1_rc_test.py
```

RC 저역통과 필터의 차단주파수를 시뮬레이션으로 구해서 이론값 1/(2 pi R C)와 비교한다.
0.24% 정도 차이가 나는데, 정확한 차단점 이득은 -3dB가 아니라 -3.01dB 이기 때문이라 정상.

## 2단계 실행

```
python examples\step2_buck_optimize.py        (기본 60회)
python examples\step2_buck_optimize.py 150    (150회)
```

12V -> 약 4.2V buck 컨버터(부하 4.2 ohm, 약 1A)의 L, C, 스위칭 주파수, 듀티를
Optuna가 바꿔가며 효율을 최대로 만드는 설계를 찾는다.

- 제약: 최대전압 4.20V 이하, 평균전압 4.10V 이상, 리플 30mV 이하
- 손실 모델: 스위치 온저항, 다이오드, L의 DCR(L이 클수록 증가),
  스위치 노드 커패시턴스(주파수가 높을수록 손실 증가), C의 ESR
  -> "L 크게 / 주파수 높게 하면 리플은 줄지만 손실이 늘어나는" trade-off가 생김
- 60회 기준 약 1분, 효율 약 93.4% 설계를 찾음 (seed=0)
- 전체 trial 기록은 `results/buck_trials.csv` (엑셀로 바로 열림)

## 새 회로 추가하는 법 (팀 공통 규칙)

회로 하나 = **템플릿(.cir) + 회로 정의(_spec.py)** 두 파일.
최적화 엔진(optimizer.py)은 건드리지 않는다.

템플릿 규칙
1. 바꿀 값은 `{{이름}}` 으로 표시 (예: `.param Lval={{L}}`)
2. batch 모드라서 `.save v(노드)` 로 측정에 쓰는 노드를 꼭 저장
3. 평가에 쓸 값은 전부 `.meas` 로 뽑기 (이름은 소문자로 받아짐)
4. 과도해석(.tran)은 정상상태 구간만 측정 (FROM=... TO=...)
5. 파일 맨 위 주석에 변수 목록과 단위 적어두기

회로 정의는 `circuits/buck_converter_spec.py` 를 복사해서
변수 범위(params), 목표(objective), 제약(constraints)만 바꾸면 된다.

## 사용 예

```python
from spice_runner import run_simulation

results, log = run_simulation("circuits/rc_lowpass.cir", {"R": 1000, "C": 100e-9})
print(results)   # {'fc': 1587.8, 'gain_10k': -16.07}
```

측정이 실패한 값은 dict에 빠져 있으므로, 최적화에서는 "필요한 값이 없으면 탈락"으로 처리한다.
