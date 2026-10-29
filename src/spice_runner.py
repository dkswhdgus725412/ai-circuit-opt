"""
spice_runner.py
- 회로 템플릿(.cir)에 파라미터 값을 채워 넣고
- ngspice를 batch 모드로 실행한 뒤
- .meas 결과를 dict로 돌려주는 모듈

최적화 엔진(Optuna)은 나중에 이 run_simulation() 함수만 반복해서 부르면 된다.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def find_ngspice():
    """
    실행할 ngspice 프로그램을 찾는다.
    Windows에서는 ngspice.exe가 창을 띄우는 GUI 버전이라
    콘솔용 ngspice_con.exe를 우선으로 쓴다.
    """
    # 1순위: 환경변수 NGSPICE_PATH 로 직접 지정한 경로
    custom = os.environ.get("NGSPICE_PATH")
    if custom and Path(custom).is_file():
        return custom

    # 2순위: PATH 에 등록된 ngspice
    for name in ("ngspice_con", "ngspice"):
        path = shutil.which(name)
        if path:
            return path

    # 3순위: Windows 기본 설치 위치 (PATH 등록을 안 했어도 동작하게)
    for candidate in (r"C:\Spice64\bin\ngspice_con.exe",
                      r"C:\Program Files\Spice64\bin\ngspice_con.exe"):
        if Path(candidate).is_file():
            return candidate

    raise FileNotFoundError(
        "ngspice를 찾을 수 없음. 설치 후 Spice64/bin 폴더를 PATH에 추가했는지, "
        "터미널을 새로 열었는지 확인할 것."
    )


def fill_template(template_path, params):
    """템플릿 안의 {{이름}} 을 params 값으로 바꾼 넷리스트 문자열을 만든다."""
    text = Path(template_path).read_text(encoding="utf-8")
    for name, value in params.items():
        text = text.replace("{{" + name + "}}", str(value))

    # 안 채워진 변수가 남아 있으면 바로 에러 (오타 잡기용)
    left = re.findall(r"\{\{(\w+)\}\}", text)
    if left:
        raise ValueError(f"값이 안 들어간 변수가 있음: {left}")
    return text


MEAS_LINE = re.compile(r"^\s*(\w+)\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def parse_measurements(output):
    """
    ngspice 출력에서 .meas 결과만 뽑는다.
    'Measurements for ... Analysis' 줄 아래 블록만 읽어서
    메모리 정보(Stack = 0 bytes 같은 줄)가 섞이지 않게 한다.
    """
    results = {}
    in_block = False
    for line in output.splitlines():
        if "Measurements for" in line:
            in_block = True
            continue
        if not in_block:
            continue
        if not line.strip():
            continue
        m = MEAS_LINE.match(line)
        if m:
            results[m.group(1).lower()] = float(m.group(2))
        elif "failed" in line or "measure" in line.lower():
            continue  # 측정 실패 줄 -> 그 값은 dict에 안 넣고 다음 줄 계속
        else:
            in_block = False  # 측정값 블록이 끝남
    return results


def run_simulation(template_path, params, timeout=30):
    """
    템플릿 + 파라미터 -> 시뮬레이션 -> 측정값 dict

    시뮬레이션이 실패하거나 측정값을 못 구하면 해당 값이 dict에 없을 수 있음.
    (최적화할 때 이런 경우는 '탈락' 처리하면 됨)
    """
    netlist = fill_template(template_path, params)

    with tempfile.TemporaryDirectory() as tmp:
        cir_file = Path(tmp) / "run.cir"
        cir_file.write_text(netlist, encoding="utf-8")
        proc = subprocess.run(
            [find_ngspice(), "-b", str(cir_file)],
            capture_output=True, text=True, timeout=timeout,
        )

    output = proc.stdout + proc.stderr
    results = parse_measurements(output)
    return results, output
