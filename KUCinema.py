from __future__ import annotations
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

"""
    github 사용법은 노션에
"""


import os
import sys
import re
from pathlib import Path
from datetime import date
from typing import Dict, Tuple, List
from collections import defaultdict
import core


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
RE_MOVIE_ID = re.compile(r"^\d{12}$")                   # YYYYMMDDHHMM
RE_TIME = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")      # HH:MM-HH:MM
RE_TITLE = re.compile(r"^(?!\s)(?!.*\s$)[0-9A-Za-z가-힣 ]+$")  # 특수문자 제외, 앞뒤 공백 금지
RE_SEAT_VECTOR = re.compile(r"^\[(?:\s*[01]\s*,){24}\s*[01]\s*\]$")  # 길이 25의 0/1
RE_BOOKING_RECORD = re.compile(
    r"^(?P<sid>\d{2})/(?P<mid>\d{12})/(?P<vec>\[(?:\s*[01]\s*,){24}\s*[01]\s*\])$"
)

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
    # try:
    #     hp = Path(os.path.expanduser("~")).resolve()  # 홈 경로 반환
    # except Exception as e:
    #     error(f"홈 경로를 파악할 수 없습니다: {e}")
    #     sys.exit(1)
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
    else:
        try:
            _ = booking_path.read_text(encoding="utf-8")
        except Exception as e:
            error(f"'{BOOKING_FILE}' 파일을 읽을 수 없습니다: {e}")
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
# 영화 데이터 파일 무결성 체크 
# ---------------------------------------------------------------

def _parse_time_bounds(t: str) -> Tuple[int, int]:
    sh, sm, eh, em = int(t[0:2]), int(t[3:5]), int(t[6:8]), int(t[9:11])
    return sh * 60 + sm, eh * 60 + em

def _valid_movie_time(s: str) -> bool:
    if not RE_TIME.fullmatch(s):
        return False
    sh, sm = int(s[0:2]), int(s[3:5])
    eh, em = int(s[6:8]), int(s[9:11])
    if not (0 <= sh <= 23 and 0 <= sm <= 59):
        return False
    if not (0 <= eh <= 99 and 0 <= em <= 59):
        return False
    start_min, end_min = _parse_time_bounds(s)
    return end_min > start_min  # 종료는 시작+1분 이상

def _valid_movie_id(mid: str) -> bool:
    if not RE_MOVIE_ID.fullmatch(mid):
        return False
    yyyy = int(mid[0:4]); mm = int(mid[4:6]); dd = int(mid[6:8])
    hh = int(mid[8:10]); m2 = int(mid[10:12])
    if yyyy < 1583:
        return False
    try:
        date(yyyy, mm, dd)
    except ValueError:
        return False
    return 0 <= hh <= 23 and 0 <= m2 <= 59

def _valid_title(title: str) -> bool:
    return RE_TITLE.fullmatch(title) is not None

def _parse_seat_vector(vec: str) -> List[int] | None:
    if not RE_SEAT_VECTOR.fullmatch(vec):
        return None
    body = vec.strip()[1:-1]
    items = [x.strip() for x in body.split(",")]
    try:
        nums = [int(x) for x in items]
    except ValueError:
        return None
    if len(nums) != 25 or any(n not in (0, 1) for n in nums):
        return None
    return nums

def validate_movie_file(movie_path: Path) -> None:
    """
    영화 파일을 처음부터 끝까지 검사.
    - 문법/의미 위배 발견 즉시 오류 출력 후 종료.
    규칙: 5필드(mid/title/date/time/seatvec), 각 필드 문법·의미,
          고유번호 오름차순, 중복 금지, 같은 날짜 상영 10개 이상 금지.
    """
    lines = movie_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        error("영화 데이터 파일이 비어 있습니다(최소 1개 레코드 필요).")
        sys.exit(1)

    prev_id_num: int | None = None
    seen_ids: set[str] = set()
    daily_counts = defaultdict(int)

    for i, line in enumerate(lines, start=1):
        if line != line.strip():
            error(f"{MOVIE_FILE}:{i}행 — 레코드 앞/뒤 공백 금지 규칙 위배.")
            sys.exit(1)

        parts = line.split("/")
        if len(parts) != 5:
            error(f"{MOVIE_FILE}:{i}행 — 필드 개수 오류(5개 아님).")
            sys.exit(1)

        mid, title, dstr, tstr, vec = parts

        if not _valid_movie_id(mid):
            error(f"{MOVIE_FILE}:{i}행 — 영화 상영표 고유번호 형식/의미 오류.")
            sys.exit(1)

        if not _valid_title(title):
            error(f"{MOVIE_FILE}:{i}행 — 영화 제목 형식 오류(특수문자/앞뒤공백 금지).")
            sys.exit(1)

        if not RE_DATE.fullmatch(dstr):
            error(f"{MOVIE_FILE}:{i}행 — 영화 날짜 문법 오류(YYYY-MM-DD).")
            sys.exit(1)
        y, m, d = int(dstr[0:4]), int(dstr[5:7]), int(dstr[8:10])
        try:
            date(y, m, d)
        except ValueError:
            error(f"{MOVIE_FILE}:{i}행 — 영화 날짜 의미 오류(존재하지 않는 날짜).")
            sys.exit(1)

        if int(mid[0:4]) != y:
            error(f"{MOVIE_FILE}:{i}행 — 고유번호 연도와 영화 날짜 연도 불일치.")
            sys.exit(1)

        if not _valid_movie_time(tstr):
            error(f"{MOVIE_FILE}:{i}행 — 영화 시간 형식/의미 오류(HH:MM-HH:MM).")
            sys.exit(1)

        if _parse_seat_vector(vec) is None:
            error(f"{MOVIE_FILE}:{i}행 — 좌석 유무 벡터 형식 오류(길이 25의 0/1 배열).")
            sys.exit(1)

        id_num = int(mid)
        if prev_id_num is not None and id_num <= prev_id_num:
            error(f"{MOVIE_FILE}:{i}행 — 고유번호 오름차순 위배(이전={prev_id_num}, 현재={id_num}).")
            sys.exit(1)
        prev_id_num = id_num

        if mid in seen_ids:
            error(f"{MOVIE_FILE}:{i}행 — 고유번호 중복 발생({mid}).")
            sys.exit(1)
        seen_ids.add(mid)

        daily_counts[dstr] += 1
        if daily_counts[dstr] >= 10:
            error(f"{MOVIE_FILE}:{i}행 — 같은 날짜({dstr}) 상영 10개 이상 규칙 위배.")
            sys.exit(1)


# ---------------------------------------------------------------
# 예매 데이터 파일 무결성 체크 
# ---------------------------------------------------------------

def validate_booking_syntax(booking_path: Path) -> None:
    """
    예매 파일 전체 문법 검사.
    - 위배 행들을 모두 수집해 한 번에 출력 후 종료.
    (의미 규칙 검사는 여기서 하지 않음)
    """
    lines = booking_path.read_text(encoding="utf-8").splitlines()
    bads: List[Tuple[int, str, str]] = []

    for i, line in enumerate(lines, start=1):
        if line.strip() == "":
            bads.append((i, line, "빈 행"))
            continue
        if line != line.strip():
            bads.append((i, line, "레코드 앞/뒤 공백 금지"))
            continue
        m = RE_BOOKING_RECORD.match(line)
        if not m:
            bads.append((i, line, "형식 불일치: 학번/영화고유번호/좌석예약벡터"))
            continue
        sid, mid, vec = m.group("sid"), m.group("mid"), m.group("vec")
        if not RE_STUDENT_ID.fullmatch(sid):
            bads.append((i, line, "학번 형식 오류(2자리 숫자)"))
        if not RE_MOVIE_ID.fullmatch(mid):
            bads.append((i, line, "영화 고유번호 형식 오류(숫자 12자리)"))
        if _parse_seat_vector(vec) is None:
            bads.append((i, line, "좌석 예약 벡터 형식 오류(길이 25의 0/1 배열)"))

    if bads:
        error("예매 데이터 파일에서 문법 규칙 위배 행이 발견되었습니다. 아래 행들을 확인하세요:")
        for li, content, reason in bads:
            print(f"  - {li}행: {content!r}  ← {reason}")
        sys.exit(1)


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
    
    # 0-2) 영화 데이터 파일 무결성(문법+의미) 검사 — 위배 발견 즉시 종료
    validate_movie_file(movie_path)

    # 0-3) 예매 데이터 파일 문법 검사 — 위배 행 전부 출력 후 종료
    validate_booking_syntax(booking_path)


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
            core.LOGGED_IN_SID = sid
            core.CURRENT_DATE_STR = CURRENT_DATE_STR
            break
        else:
            # 신규 회원 → 6.2.4
            prompt_password_new(student_path, sid, students)
            LOGGED_IN_SID = sid
            info(f"환영합니다, {LOGGED_IN_SID}님! 주 프롬프트로 이동합니다.")
            core.LOGGED_IN_SID = sid
            core.CURRENT_DATE_STR = CURRENT_DATE_STR
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
