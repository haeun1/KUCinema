#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KU 영화 예매 프로그램 — KUCinema.py

이 파일은 기획서의 6장 중 다음을 구현합니다.
  • 6.1 날짜 입력 프롬프트 (입력 날짜 검증 및 설정)
  • 6.2 로그인 프롬프트 (학번 입력 → 로그인 의사 → 기존/신규 분기 → 비밀번호 입력/설정)
  • 6.3 주 프롬프트 (메뉴 1~4와 0 종료 / 외부 모듈로 디스패치)

※ 데이터 파일 관련
  - 홈 경로({HOME}) 기준으로 다음 파일을 사용합니다.
      movie-schedule.txt : 반드시 존재해야 하며(읽기 가능), 없으면 즉시 종료
      student-info.txt   : 없으면 빈 파일 생성
      booking-info.txt   : 없으면 빈 파일 생성
  - 학생 데이터 파일(student-info.txt)은 프로그램 시작 시 최소 무결성(형식/중복) 검사를 수행합니다.

※ 메뉴 디스패치
  - 사용자가 ‘1’~‘4’를 선택하면 각각 menu1.py~menu4.py의 동일한 함수명(menu1, menu2, ...)을 실행합니다.
  - 모듈/함수가 없을 경우 친절한 오류 메시지를 출력하고 주 프롬프트로 복귀합니다.

Python 3.11 표준 라이브러리만 사용합니다.
"""

from __future__ import annotations

import os
import sys
import re
from pathlib import Path
from datetime import date
from typing import Dict, Tuple

# ---------------------------------------------------------------
# 상수 정의
# ---------------------------------------------------------------
MOVIE_FILE = "movie-schedule.txt"
STUDENT_FILE = "student-info.txt"
BOOKING_FILE = "booking-info.txt"

# 정규식 패턴 (문법 형식)
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")          # YYYY-MM-DD
RE_STUDENT_ID = re.compile(r"^\d{2}$")                  # 2자리 숫자
RE_PASSWORD = re.compile(r"^\d{4}$")                   # 4자리 숫자
RE_STUDENT_RECORD = re.compile(r"^(?P<sid>\d{2})/(?P<pw>\d{4})$")  # 학생 레코드 형식

# 전역 상태 (필수 컨텍스트)
CURRENT_DATE_STR: str | None = None  # 내부 현재 날짜(문자열, YYYY-MM-DD)
LOGGED_IN_SID: str | None = None     # 로그인된 학번(2자리)


# ---------------------------------------------------------------
# 유틸리티 출력
# ---------------------------------------------------------------
def info(msg: str) -> None:
    print(msg)

def warn(msg: str) -> None:
    print(f"[경고] {msg}")

def error(msg: str) -> None:
    print(f"[오류] {msg}")


# ---------------------------------------------------------------
# 파일/환경 준비
# ---------------------------------------------------------------
def home_path() -> Path:
    #hp = Path(os.path.expanduser("~")).resolve() # 홈 경로 반환
    
    # 배포하기 전은 현재 경로인 KUCinema.py 파일의 경로를 반환
    hp = Path(os.getcwd())
    #print("현재 경로:", os.getcwd())
    return hp


def ensure_environment() -> Tuple[Path, Path, Path]:
    """필수 파일 존재/권한 확인 및 학생/예매 파일 생성.

    return: (movie_path, student_path, booking_path)
    """
    hp = home_path()
    movie_path = hp / MOVIE_FILE
    student_path = hp / STUDENT_FILE
    booking_path = hp / BOOKING_FILE

    # 1) 영화 데이터 파일: 존재 + 읽기 권한 필수
    if not movie_path.exists():
        error(f"홈 경로에 '{MOVIE_FILE}' 파일이 없습니다. 프로그램을 종료합니다.")
        sys.exit(1)
    try:
        _ = movie_path.read_text(encoding="utf-8")
    except Exception as e:
        error(f"'{MOVIE_FILE}' 파일을 읽을 수 없습니다: {e}")
        sys.exit(1)

    # 2) 학생 데이터 파일: 없으면 빈 파일 생성, 있으면 읽기/쓰기 가능 확인
    if not student_path.exists():
        warn(f"'{STUDENT_FILE}' 파일이 없어 빈 파일을 생성합니다.")
        try:
            student_path.write_text("", encoding="utf-8", newline="\n")
            info(f"'{STUDENT_FILE}' 파일 생성 완료.")
        except Exception as e:
            error(f"'{STUDENT_FILE}' 파일 생성 실패: {e}")
            sys.exit(1)
    else:
        try:
            _ = student_path.read_text(encoding="utf-8")
        except Exception as e:
            error(f"'{STUDENT_FILE}' 파일을 읽을 수 없습니다: {e}")
            sys.exit(1)

    # 3) 예매 데이터 파일: 없으면 빈 파일 생성 (6.1~6.3에서는 직접 사용하지 않지만 미리 준비)
    if not booking_path.exists():
        warn(f"'{BOOKING_FILE}' 파일이 없어 빈 파일을 생성합니다.")
        try:
            booking_path.write_text("", encoding="utf-8", newline="\n")
            info(f"'{BOOKING_FILE}' 파일 생성 완료.")
        except Exception as e:
            error(f"'{BOOKING_FILE}' 파일 생성 실패: {e}")
            sys.exit(1)

    return movie_path, student_path, booking_path


# ---------------------------------------------------------------
# 학생 파일 무결성 체크 (형식/중복)
# ---------------------------------------------------------------
def load_and_validate_students(student_path: Path) -> Dict[str, str]:
    """학생 데이터 파일을 읽고 최소 무결성 점검.

    - 각 행은 반드시 "NN/NNNN" 형식이어야 함
    - 학번 중복 금지
    - 공백 행/공백류 행 금지(파일에 등장하면 오류)
    """
    raw = student_path.read_text(encoding="utf-8").splitlines()
    students: Dict[str, str] = {}
    bad_lines: list[Tuple[int, str]] = []

    for idx, line in enumerate(raw, start=1):
        if line.strip() == "":
            # 기획서 5.2.1: 모든 행이 학생 레코드여야 하므로 공백행도 오류로 간주
            bad_lines.append((idx, line))
            continue
        m = RE_STUDENT_RECORD.match(line)
        if not m:
            bad_lines.append((idx, line))
            continue
        sid = m.group("sid")
        pw = m.group("pw")
        if sid in students:
            bad_lines.append((idx, line))  # 중복도 오류로 보임
            continue
        students[sid] = pw

    if bad_lines:
        error("학생 데이터 파일 형식 오류 또는 중복 학번이 있습니다. 다음 행을 확인하세요:")
        for li, content in bad_lines:
            print(f"  - {li}행: {content!r}")
        sys.exit(1)

    return students


# ---------------------------------------------------------------
# 날짜(6.1) — 문법/의미 검증
# ---------------------------------------------------------------
def is_valid_date_string(s: str) -> bool:
    """YYYY-MM-DD 형식 + 실제 존재하는 날짜 + 연도 첫 자리가 0이 아님"""
    if not RE_DATE.fullmatch(s):
        return False
    if s[0] == "0":
        return False  # 연도 첫 자리는 0 불가
    y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
    try:
        date(y, m, d)
    except ValueError:
        return False
    return True


def prompt_input_date() -> str:
    """6.1 날짜 입력 프롬프트"""
    while True:
        s = input("현재 날짜를 설정하세요 (YYYY-MM-DD): ")
        # 문법/의미 체크
        if not RE_DATE.fullmatch(s):
            error("입력 날짜의 문법 형식이 올바르지 않습니다. 예: 2025-10-03")
            continue
        if not is_valid_date_string(s):
            error("입력한 날짜가 실제 달력에 존재하지 않습니다. 다시 입력하세요.")
            continue
        return s


# ---------------------------------------------------------------
# 로그인 플로우(6.2)
# ---------------------------------------------------------------
def prompt_student_id() -> str:
    """6.2.1 학번 입력 — 문법 형식: 2자리 숫자, 공백 불가"""
    while True:
        sid = input("학번(2자리 숫자): ")
        if not RE_STUDENT_ID.fullmatch(sid):
            error("학번의 문법 형식이 올바르지 않습니다. 예: 00, 07, 42")
            continue
        return sid


def prompt_login_intent() -> bool:
    """6.2.2 로그인 의사 — 'Y'만 긍정, 나머지는 모두 부정"""
    ans = input("해당 학번으로 로그인/가입을 진행할까요? (Y/N): ")
    return ans == "Y"


def prompt_password_existing(expected_pw: str) -> bool:
    """6.2.3 기존 회원 비밀번호 입력.
    - 문법 형식 위배: 현재 단계(비밀번호 입력) 재시작
    - 의미 규칙 위배(불일치): 6.2.1 학번 입력으로 되돌아가야 하므로 False 반환
    - 정상: True 반환
    """
    while True:
        pw = input("비밀번호(4자리 숫자): ")
        if not RE_PASSWORD.fullmatch(pw):
            error("비밀번호의 문법 형식이 올바르지 않습니다. 예: 0000, 0420, 1234")
            continue  # 6.2.3 재시작
        if pw != expected_pw:
            error("비밀번호가 일치하지 않습니다. 처음(학번 입력)으로 돌아갑니다.")
            return False  # 6.2.1로 복귀
        # 정상
        return True


def prompt_password_new(student_path: Path, sid: str, students: Dict[str, str]) -> None:
    """6.2.4 신규 회원: 비밀번호 설정 후 파일에 <학번>/<비밀번호> 추가"""
    while True:
        pw = input("새 비밀번호(4자리 숫자): ")
        if not RE_PASSWORD.fullmatch(pw):
            error("비밀번호의 문법 형식이 올바르지 않습니다. 예: 0000, 0420, 1234")
            continue
        # 파일에 추가
        with student_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(f"{sid}/{pw}\n")
        students[sid] = pw
        info("신규 회원 가입이 완료되었습니다.")
        break


# ---------------------------------------------------------------
# 주 프롬프트(6.3) & 메뉴 디스패치
# ---------------------------------------------------------------
def show_main_menu() -> None:
    print()
    print("================= 주 프롬프트 =================")
    print("1) 영화 예매")
    print("2) 예매 내역 조회")
    print("3) 예매 취소")
    print("4) 상영 시간표 조회")
    print("0) 종료")
    print("==============================================")


def dispatch_menu(choice: str) -> None:
    """외부 모듈(menu1~menu4)의 동일 함수(menu1~menu4)를 호출.
    모듈/함수 미존재 시 오류 메시지 후 복귀.
    """
    module_name = f"menu{choice}"
    func_name = f"menu{choice}"

    try:
        mod = __import__(module_name)
    except Exception as e:
        error(f"메뉴 모듈 '{module_name}.py'을(를) 불러올 수 없습니다: {e}")
        return

    func = getattr(mod, func_name, None)
    if not callable(func):
        error(f"'{module_name}.py' 안에 함수 '{func_name}()'가 없습니다.")
        return

    try:
        # 기획서/요청: menu1() 식으로 인자 없이 호출
        func()
    except TypeError as te:
        error(f"함수 호출 형식 오류: {module_name}.{func_name}(): {te}")
    except SystemExit:
        raise
    except Exception as e:
        error(f"메뉴 실행 중 예외가 발생했습니다: {e}")


def main_prompt_loop() -> None:
    """6.3 주 프롬프트 — 입력 검증 및 분기"""
    while True:
        show_main_menu()
        s = input("메뉴를 선택하세요 (1/2/3/4/0): ")

        # 문법 형식: 숫자만의 길이 1
        if not re.fullmatch(r"\d", s or ""):
            error("문법 형식 위배: 한 자리 숫자만 입력하세요.")
            continue

        # 의미 규칙: {1,2,3,4,0}
        if s not in {"1", "2", "3", "4", "0"}:
            error("의미 규칙 위배: 1,2,3,4,0 중 하나를 입력하세요.")
            continue

        if s == "0":
            info("프로그램을 종료합니다.")
            sys.exit(0)

        # 1~4: 해당 메뉴 모듈로 디스패치
        dispatch_menu(s)


# ---------------------------------------------------------------
# 엔트리포인트: 전체 플로우 결합
# ---------------------------------------------------------------
def main() -> None:
    global CURRENT_DATE_STR, LOGGED_IN_SID

    # 0) 환경 준비
    movie_path, student_path, booking_path = ensure_environment()

    # 0-1) 학생 파일 최소 무결성 검사
    students = load_and_validate_students(student_path)

    # 1) 6.1 — 날짜 입력
    CURRENT_DATE_STR = prompt_input_date()  # 내부 현재 날짜 확정

    # 2) 6.2 — 로그인 플로우
    while True:
        sid = prompt_student_id()  # 6.2.1
        if not prompt_login_intent():  # 6.2.2 (부정이면 학번 입력 재시작)
            continue

        if sid in students:  # 기존 회원 → 6.2.3
            ok = prompt_password_existing(students[sid])
            if not ok:
                # 의미 규칙 위배(비밀번호 불일치) → 6.2.1로 되돌아감
                continue
            # 정상 로그인
            LOGGED_IN_SID = sid
            info(f"환영합니다, {LOGGED_IN_SID}님! 주 프롬프트로 이동합니다.")
            break
        else:
            # 신규 회원 → 6.2.4
            prompt_password_new(student_path, sid, students)
            LOGGED_IN_SID = sid
            info(f"환영합니다, {LOGGED_IN_SID}님! 주 프롬프트로 이동합니다.")
            break

    # 3) 6.3 — 주 프롬프트
    main_prompt_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()  # 줄바꿈 정리
        warn("사용자에 의해 종료되었습니다.")
        sys.exit(130)
