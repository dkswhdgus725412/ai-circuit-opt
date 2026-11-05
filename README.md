# AI 기반 회로 자동 설계 최적화

회생제동 기반 배터리-모터 통합 구동 시스템의 컨버터 / 모터 구동회로 설계 파라미터를
ngspice + Optuna (+ LLM)로 자동 최적화하는 프로젝트.

## 진행 단계

- [x] 1단계: Python에서 ngspice 실행하고 측정값 받아오기
- [x] 2단계: 기본 buck 컨버터로 Optuna 최적화 루프 완성
- [x] 3단계: baseline(손계산 설계)과 AI 결과 비교
- [ ] 4단계: 팀원 실제 회로(컨버터 / 모터 구동)로 교체
- [ ] 5단계: LLM 레이어 추가 (선택)

## 폴더 구조

```
ai-circuit-opt/
  circuits/
    rc_lowpass.cir            1단계 테스트 회로
    buck_converter.cir        2단계 buck 컨버터 템플릿
    buck_converter_spec.py    buck 회로 정의 (변수 범위, 제약, 목표)
    buck_baseline.py          사람이 교과서 공식으로 손계산한 baseline 설계
  src/
    spice_runner.py           템플릿 채우기 -> ngspice 실행 -> .meas 결과 dict
    circuit_spec.py           회로 정의 형식 (팀 공통)
    optimizer.py              Optuna 최적화 엔진 (팀 공통)
  examples/                   단계별 실행 스크립트
  results/                    실행 결과 CSV (git에는 안 올라감)
```

## 설치

### Arch Linux (bash / zsh)

시스템 ngspice와 Python 가상환경을 사용한다.
시스템 패키지는 전체 업그레이드와 함께 설치한다. 프로젝트 루트에서 실행:

```sh
sudo pacman -Syu --needed python python-pip ngspice

python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

ngspice --version
python examples/step1_rc_test.py
python examples/step2_buck_optimize.py
python examples/step3_compare_baseline.py
```

- 프로젝트 의존성은 위에서 만든 가상환경에 설치한다.
- 새 터미널에서는 프로젝트 루트에서 `source .venv/bin/activate`로 활성화한다.
  fish에서는 `source .venv/bin/activate.fish`를 사용한다.
- 가상환경의 Python을 직접 지정해 `.venv/bin/python examples/step1_rc_test.py`로 실행할 수 있다.
- Python의 minor 버전 업데이트 후에는 새 가상환경을 만들고 의존성을 설치한다.
- ngspice는 PATH에서 자동 탐색한다.
  실행 파일을 직접 지정하려면 `export NGSPICE_PATH=/usr/bin/ngspice`를 사용한다.
  PATH 자동 탐색으로 전환하려면 `unset NGSPICE_PATH`를 실행한다.
  `NGSPICE_PATH`에는 실행 가능한 파일 경로를 지정한다.
- 비교 그래프는 PNG 파일로 저장한다.

검증 환경: Arch Linux, Python 3.14.9, ngspice 47, NumPy 2.5.4,
Optuna 5.0.0, Matplotlib 3.11.2에서 1~3단계 실행을 확인했다.

Arch/Linux 회귀 테스트 (가상환경 활성화 후):

```sh
python -m unittest discover -s tests -p test_spice_runner.py -v
```

실제 RC 시뮬레이션 테스트는 PATH에 `ngspice`가 등록된 환경에서 실행한다.

### 다른 OS: ngspice
- Windows: https://ngspice.sourceforge.io/download.html 에서 받아서 압축을 풀고
  `Spice64` 폴더를 `C:\Spice64` 에 둔다.
  - `C:\Spice64` 에 두면 PATH 등록을 안 해도 코드가 자동으로 찾는다.
  - 다른 곳에 뒀다면 PATH에 `...\Spice64\bin` 을 추가하거나,
    환경변수 `NGSPICE_PATH` 에 `ngspice_con.exe` 전체 경로를 넣는다.
  - ngspice.exe는 창을 띄우는 GUI 버전이라 코드는 ngspice_con.exe를 쓴다.
- Mac: `brew install ngspice`
- Ubuntu: `sudo apt install ngspice`

확인: `C:\Spice64\bin\ngspice_con.exe --version` 에서 버전이 나오면 성공.

### Windows: Python + 가상환경 (명령 프롬프트)

Windows는 기존 Python 3.13 환경을 사용하고, Arch에서는 Python 3.14.9로 실행을 확인했다.

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
python examples/step1_rc_test.py
```

RC 저역통과 필터의 차단주파수를 시뮬레이션으로 구해서 이론값 1/(2 pi R C)와 비교한다.
0.24% 정도 차이가 나는데, 정확한 차단점 이득은 -3dB가 아니라 -3.01dB 이기 때문이라 정상.

## 2단계 실행

기본 60회 실행 또는 인자로 150회 지정:

```
python examples/step2_buck_optimize.py
python examples/step2_buck_optimize.py 150
```

12V -> 약 4.2V buck 컨버터(부하 4.2 ohm, 약 1A)의 L, C, 스위칭 주파수, 듀티를
Optuna가 바꿔가며 효율을 최대로 만드는 설계를 찾는다.

- 제약: 최대전압 4.20V 이하, 평균전압 4.10V 이상, 리플 30mV 이하
- 손실 모델: 스위치 온저항, 다이오드, L의 DCR(L이 클수록 증가),
  스위치 노드 커패시턴스(주파수가 높을수록 손실 증가), C의 ESR
  -> "L 크게 / 주파수 높게 하면 리플은 줄지만 손실이 늘어나는" trade-off가 생김
- 60회 기준 약 1분, 효율 약 93.4% 설계를 찾음 (seed=0)
- 전체 trial 기록은 `results/buck_trials.csv` (엑셀로 바로 열림)

## 3단계 실행

seed 3개를 각각 기본 60회 실행하거나, 인자로 각각 100회 지정:

```
python examples/step3_compare_baseline.py
python examples/step3_compare_baseline.py 100
```

같은 buck 컨버터를 사람이 손계산한 설계 2개와 AI 설계를 비교한다.

- 사람 A: 이상적 공식 D = Vout/Vin (손실 무시)
- 사람 B: 손실 보정 공식 D = (Vout+Vd)/(Vin-Vsw+Vd), fsw 200kHz, 리플전류 40%, C 여유 2배, E6 표준값
- AI: Optuna, seed 0/1/2 (운이 아니라는 걸 보여주려고 여러 번)

결과 (60회 기준)

| 설계 | 효율 [%] | 평균전압 [V] | 리플 [mV] | 조건 |
|---|---|---|---|---|
| 사람 A | 92.78 | 3.882 | 10.5 | X (평균전압 미달) |
| 사람 B | 93.19 | 4.121 | 10.6 | O |
| AI seed 0 | 93.44 | 4.170 | 6.9 | O |
| AI seed 1 | 93.51 | 4.121 | 9.2 | O |
| AI seed 2 | 93.52 | 4.173 | 14.4 | O |

- AI가 사람 B보다 평균 +0.30 %p (seed 3개 모두 +0.25 이상)
- 이 회로는 손실 요소가 단순해서 효율 차이가 작다. 실제 팀 회로(손실 요소가 많고
  변수가 서로 얽힌 회로)로 바꾸면 차이가 더 커질 것으로 예상
- 결과 파일: `results/step3_comparison.csv`, `results/step3_convergence.png`
