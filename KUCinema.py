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
import ast


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
    print(f"..! 경고: {msg}")

def error(msg: str) -> None:
    print(f"!!! 오류: {msg}")


# ---------------------------------------------------------------
# 파일/환경 준비
# ---------------------------------------------------------------
def home_path() -> Path:
    hp = Path(os.path.expanduser("~")).resolve() # 홈 경로 반환
    try:
        hp = Path(os.path.expanduser("~")).resolve()  # 홈 경로 반환
    except Exception as e:
        error(f"홈 경로를 파악할 수 없습니다! 프로그램을 종료합니다. {e}")
        sys.exit(1)
    # 배포하기 전은 현재 경로인 KUCinema.py 파일의 경로를 반환
    # hp = Path(os.getcwd())
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
        error(f"영화 데이터 파일 \n홈 경로에 영화 데이터 파일({MOVIE_FILE})이 존재하지 않습니다. 프로그램을 종료합니다.")
        sys.exit(1)
    try:
        _ = movie_path.read_text(encoding="utf-8")
    except Exception as e:
        error(f"{movie_path}'에 대한 읽기 권한이 없습니다! 프로그램을 종료합니다. {e}")
        sys.exit(1)

    # 2) 학생 데이터 파일: 없으면 빈 파일 생성, 있으면 읽기/쓰기 가능 확인
    if not student_path.exists():
        warn(f"홈 경로 {hp}에 학생 데이터 파일이 없습니다.")
        try:
            student_path.write_text("", encoding="utf-8", newline="\n")
            info(f"... 홈 경로에 빈 학생 데이터 파일을 새로 생성했습니다: \n{student_path}")
        except Exception as e:
            error(f"홈 경로에 학생 데이터 파일을 생성하지 못했습니다! 프로그램을 종료합니다.")
            sys.exit(1)
    else:
        try:
            _ = student_path.read_text(encoding="utf-8")
        except Exception as e:
            error(f"데이터 파일\n{student_path}에 대한 입출력 권한이 없습니다! 프로그램을 종료합니다.")
            sys.exit(1)

    # 3) 예매 데이터 파일: 없으면 빈 파일 생성 (6.1~6.3에서는 직접 사용하지 않지만 미리 준비)
    if not booking_path.exists():
        warn(f"홈 경로 {hp}에 예매 데이터 파일이 없습니다.")
        try:
            booking_path.write_text("", encoding="utf-8", newline="\n")
            info(f"... 홈 경로에 빈 예매 데이터 파일을 새로 생성했습니다:\n{booking_path}")
        except Exception as e:
            error(f"홈 경로에 예메 데이터파일을 생성하지 못했습니다! 프로그램을 종료합니다.")
            sys.exit(1)
    else:
        try:
            _ = booking_path.read_text(encoding="utf-8")
        except Exception as e:
            error(f"데이터 파일\n{booking_path}\n에 대한 입출력 권한이 없습니다! 프로그램을 종료합니다.")
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
        error("데이터 파일\n{student_path}가 올바르지 않습니다! 프로그램을 종료합니다.")
        for li, content in bad_lines:
            #print(f"  - {li}행: {content!r}")
            print(f"{content}")
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
        #error("영화 데이터 파일이 비어 있습니다(최소 1개 레코드 필요).")
        error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
        sys.exit(1)

    prev_id_num: int | None = None
    seen_ids: set[str] = set()
    daily_counts = defaultdict(int)

    for i, line in enumerate(lines, start=1):
        if line != line.strip():
            #error(f"{MOVIE_FILE}:{i}행 — 레코드 앞/뒤 공백 금지 규칙 위배.")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)

        parts = line.split("/")
        if len(parts) != 5:
            #error(f"{MOVIE_FILE}:{i}행 — 필드 개수 오류(5개 아님).")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)

        mid, title, dstr, tstr, vec = parts

        if not _valid_movie_id(mid):
            #error(f"{MOVIE_FILE}:{i}행 — 영화 상영표 고유번호 형식/의미 오류.")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)

        if not _valid_title(title):
            #error(f"{MOVIE_FILE}:{i}행 — 영화 제목 형식 오류(특수문자/앞뒤공백 금지).")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)

        if not RE_DATE.fullmatch(dstr):
            #error(f"{MOVIE_FILE}:{i}행 — 영화 날짜 문법 오류(YYYY-MM-DD).")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)
        y, m, d = int(dstr[0:4]), int(dstr[5:7]), int(dstr[8:10])
        try:
            date(y, m, d)
        except ValueError:
            #error(f"{MOVIE_FILE}:{i}행 — 영화 날짜 의미 오류(존재하지 않는 날짜).")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)

        if int(mid[0:4]) != y:
            #error(f"{MOVIE_FILE}:{i}행 — 고유번호 연도와 영화 날짜 연도 불일치.")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)

        if not _valid_movie_time(tstr):
            #error(f"{MOVIE_FILE}:{i}행 — 영화 시간 형식/의미 오류(HH:MM-HH:MM).")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)

        if _parse_seat_vector(vec) is None:
            #error(f"{MOVIE_FILE}:{i}행 — 좌석 유무 벡터 형식 오류(길이 25의 0/1 배열).")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)

        id_num = int(mid)
        if prev_id_num is not None and id_num <= prev_id_num:
            #error(f"{MOVIE_FILE}:{i}행 — 고유번호 오름차순 위배(이전={prev_id_num}, 현재={id_num}).")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)
        prev_id_num = id_num

        if mid in seen_ids:
            #error(f"{MOVIE_FILE}:{i}행 — 고유번호 중복 발생({mid}).")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
            sys.exit(1)
        seen_ids.add(mid)

        daily_counts[dstr] += 1
        if daily_counts[dstr] >= 10:
            #error(f"{MOVIE_FILE}:{i}행 — 같은 날짜({dstr}) 상영 10개 이상 규칙 위배.")
            error(f"영화 데이터 파일\n데이터 파일에 규칙에 위배되는 행이 존재합니다. 프로그램을 종료합니다.")
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
        error(f"데이터 파일\n{booking_path}가 올바르지 않습니다! 프로그램을 종료합니다.")
        for li, content, reason in bads:
            #print(f"  - {li}행: {content!r}  ← {reason}")
            print(f"{content}")
        sys.exit(1)
    
    

    
def prune_zero_seat_bookings(booking_path: Path) -> None:
    """
    좌석 예약 벡터가 모두 0인 예매 레코드를 경고 표시 후 파일에서 삭제.
    (5.3.3 부가 확인 항목)
    """
    lines = booking_path.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    removed = 0

    for line in lines:
        line_stripped = line.strip()
        if line_stripped == "":
            # 빈 행은 validate_booking_syntax에서 이미 걸러짐. 안전 차원에서 보존하지 않음.
            continue
        m = RE_BOOKING_RECORD.match(line_stripped)
        if not m:
            # 문법 검증 이후 단계이므로 일반적으로 도달하지 않음. 안전하게 유지.
            kept.append(line_stripped)
            continue
        vec_str = m.group("vec")
        vec = _parse_seat_vector(vec_str)
        if vec is None:
            # 문법 검증 이후 단계이므로 일반적으로 도달하지 않음. 안전하게 유지.
            kept.append(line_stripped)
            continue
        if all(v == 0 for v in vec):
            #warn(f"좌석 예약 벡터가 모두 0인 예매 레코드를 삭제합니다: {line_stripped}")
            removed += 1
            continue
        kept.append(line_stripped)

    if removed > 0:
        warn(f"예매 데이터 파일에 무의미한 예매 레코드가 존재합니다. 해당 예매 레코드를 삭제합니다.")
        booking_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8", newline="\n")
    

# ---------------------------------------------------------------
# 좌석 일관성 규칙
# ---------------------------------------------------------------
def validate_booking_vectors():
    # 1. 경로 설정
    movie_path = home_path() / MOVIE_FILE
    booking_path = home_path() / BOOKING_FILE

    # 2. movie-schedule 파일 → 좌석 유무 벡터 읽기
    movie_vectors = {}
    with movie_path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("/")
            movie_id = parts[0]
            seat_vector = ast.literal_eval(parts[-1])
            movie_vectors[movie_id] = seat_vector

    # 3. booking-info 파일 → 좌석 예약 벡터 누적
    booking_sum_vectors = defaultdict(lambda: [0] * 25)
    with booking_path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("/")
            movie_id = parts[1]
            booking_vector = ast.literal_eval(parts[-1])
            for i in range(25):
                booking_sum_vectors[movie_id][i] += booking_vector[i]

    # 4. 검증
    all_passed = True
    for movie_id, summed_vector in booking_sum_vectors.items():
        if movie_id not in movie_vectors:
            #print(f"movie-schedule에 존재하지 않는 movie_id: {movie_id}")
            all_passed = False
            continue

        if summed_vector != movie_vectors[movie_id]:
            #print(f"불일치: movie_id {movie_id}")
            #print(f"  예약 벡터 합: {summed_vector}")
            #print(f"  movie-schedule 벡터: {movie_vectors[movie_id]}")
            all_passed = False

    # 5. 결과 처리
    if all_passed:
        return
    else:
        #print("영화 데이터 파일과 예매 데이터 파일 사이의 불일치가 발생했습니다.")
        #print("프로그램을 종료합니다.")
        error(f" 데이터 파일\n{booking_path}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        sys.exit(1)

# ---------------------------------------------------------------
# 영화 고유번호 참조 규칙
# ---------------------------------------------------------------
def check_invalid_movie_id():
    movie_path = home_path() / MOVIE_FILE
    booking_path = home_path() / BOOKING_FILE

    # 1. 영화 데이터에 존재하는 movie_id 수집
    valid_movie_ids = set()
    with movie_path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("/")
            if len(parts) >= 1:
                valid_movie_ids.add(parts[0])

    # 2. 예매 데이터에서 movie_id 검증
    invalid_lines = []
    with booking_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            parts = line.split("/")
            if len(parts) != 3:
                continue
            movie_id = parts[1]
            if movie_id not in valid_movie_ids:
                invalid_lines.append(line)

    # 3. 출력 및 종료
    if invalid_lines:
        #print("!!! 오류: 존재하지 않는 영화 고유번호를 참조하는 예매 레코드가 있습니다:")
        error(f"데이터 파일\n{booking_path}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        for line in invalid_lines:
            print(line)
        #print("프로그램을 종료합니다.")
        sys.exit(1)
 
# ---------------------------------------------------------------
# 학생 학번 참조 규칙
# ---------------------------------------------------------------
def check_invalid_student_id():
    student_path = home_path() / STUDENT_FILE
    booking_path = home_path() / BOOKING_FILE

    # 1. 유효한 학번 수집
    valid_student_ids = set()
    with student_path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("/")
            if parts:
                valid_student_ids.add(parts[0])

    # 2. 예매 데이터에서 학번 검증
    invalid_lines = []
    with booking_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            parts = line.split("/")
            if len(parts) != 3:
                continue
            student_id = parts[0]
            if student_id not in valid_student_ids:
                invalid_lines.append(line)

    # 3. 결과 처리
    if invalid_lines:
        #print("!!! 오류: 존재하지 않는 학번을 참조하는 예매 레코드가 있습니다:")
        error(f"데이터 파일\n{booking_path}가 올바르지 않습니다!\n의미 규칙이 위반되었습니다. 프로그램을 종료합니다.")
        for line in invalid_lines:
            print(line)
        #print("프로그램을 종료합니다.")
        sys.exit(1)


# ---------------------------------------------------------------
# 6.4.(5) 무결성 검사 - 전체 모두 실행하는 함수 (예매 파일 의미 규칙)
# ---------------------------------------------------------------
def validate_all_booking_rules():

    check_invalid_student_id()
    check_invalid_movie_id()
    validate_booking_vectors()

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
        # 그레고리력 시작일(1582년 10월 15일) 이전의 날짜는 거부
        if y < 1582 or (y == 1582 and m < 10) or (y == 1582 and m == 10 and d < 15):
            return False
        date(y, m, d)
    except ValueError:
        return False
    return True


def prompt_input_date() -> str:
    """6.1 날짜 입력 프롬프트"""
    while True:
        s = input("현재 날짜를 입력하세요 (YYYY-MM-DD) : ")
        # 문법/의미 체크
        if not RE_DATE.fullmatch(s):
            info("날짜 형식이 맞지 않습니다. 다시 입력해주세요")
            continue
        if not is_valid_date_string(s):
            info("존재하지 않는 날짜입니다. 다시 입력해주세요.")
            continue
        return s


# ---------------------------------------------------------------
# 로그인 플로우(6.2)
# ---------------------------------------------------------------
def prompt_student_id() -> str:
    """6.2.1 학번 입력 — 문법 형식: 2자리 숫자, 공백 불가"""
    while True:
        sid = input("학번을 입력하세요 (2자리 숫자) : ")
        if not RE_STUDENT_ID.fullmatch(sid):
            info("학번의 형식이 올바르지 않습니다. 다시 입력해주세요.")
            continue
        return sid


def prompt_login_intent(sid: str) -> bool:
    """6.2.2 로그인 의사 — 'Y'만 긍정, 나머지는 모두 부정"""
    ans = input(f"{sid} 님으로 로그인하시겠습니까? (Y/N) : ")
    return ans == "Y"


def prompt_password_existing(expected_pw: str) -> bool:
    """6.2.3 기존 회원 비밀번호 입력.
    - 문법 형식 위배: 현재 단계(비밀번호 입력) 재시작
    - 의미 규칙 위배(불일치): 6.2.1 학번 입력으로 되돌아가야 하므로 False 반환
    - 정상: True 반환
    """
    while True:
        pw = input("비밀번호를 입력하세요 (4자리 숫자) : ")
        if not RE_PASSWORD.fullmatch(pw):
            info("비밀번호의 형식이 올바르지 않습니다. 다시 입력해주세요.")
            continue  # 6.2.3 재시작
        if pw != expected_pw:
            info("비밀번호가 올바르지 않습니다.")
            return False  # 6.2.1로 복귀
        # 정상
        return True


def prompt_password_new(student_path: Path, sid: str, students: Dict[str, str]) -> None:
    """6.2.4 신규 회원: 비밀번호 설정 후 파일에 <학번>/<비밀번호> 추가"""
    while True:
        pw = input("신규 회원입니다. 비밀번호를 설정해주세요 (4자리 숫자) : ")
        if not RE_PASSWORD.fullmatch(pw):
            info("비밀번호의 형식이 올바르지 않습니다. 다시 입력해주세요.")
            continue
        # 파일에 추가
        with student_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(f"\n{sid}/{pw}")
        students[sid] = pw
        #info("신규 회원 가입이 완료되었습니다.")
        break


# ---------------------------------------------------------------
# 메뉴 구현 (menu1 ~ menu4)
# ---------------------------------------------------------------

# ===== menu1: 영화 예매 =====
# 기본 좌석 설정
ROWS = ["A", "B", "C", "D", "E"]
COLS = [1, 2, 3, 4, 5]

def create_seat_buffer(seat_vector: list[int]) -> dict[str, int]:
    """
    영화의 좌석 유무 벡터(길이 25, 0/1)를 
    {'A1':0, 'A2':1, ..., 'E5':1} 형태로 변환
    """
    seat_buffer: dict[str, int] = {}
    idx = 0
    for row in ROWS:
        for col in COLS:
            seat_id = f"{row}{col}"
            seat_buffer[seat_id] = seat_vector[idx]
            idx += 1
    return seat_buffer

def print_seat_board(seat_buffer: dict[str, int]) -> None:
    """
    좌석 버퍼를 기반으로 현재 좌석 상태를 콘솔에 시각화하여 출력
    - '□' : 예매 가능 (0)
    - '■' : 이미 예매됨 (1)
    - '*' : 이번 예매에서 방금 선택한 좌석 (2)
    """
    print("빈 사각형은 예매 가능한 좌석입니다.")
    print("   스크린")
    print("   ", " ".join(str(c) for c in COLS))

    for row in ROWS:
        line: list[str] = [f"{row}"]
        for col in COLS:
            seat_id = f"{row}{col}"
            val = seat_buffer[seat_id]
            if val == 0:
                line.append("□")  # 예매 가능
            elif val == 1:
                line.append("■")  # 이미 예매됨
            elif val == 2:
                #line.append("★")  # 현재 예매 중
                line.append("■")  # 현재 예매 중
        print(" ", " ".join(line))

def select_date() -> str | None:
    """
    6.4.1 날짜 선택
    - 영화 데이터 파일에서 현재 날짜 이후의 상영 날짜를 제시하고 선택을 받음
    - 정상 입력 시 해당 날짜 문자열을 반환
    - '0' 입력 시 None 반환 (주 프롬프트 복귀)
    """
    if CURRENT_DATE_STR is None:
        error("내부 현재 날짜가 설정되어 있지 않습니다.")
        return None

    movie_path = home_path() / MOVIE_FILE
    lines = movie_path.read_text(encoding="utf-8").splitlines()

    dates: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("/")
        if len(parts) < 5:
            continue
        _, _, movie_date, _, _ = parts
        if movie_date > CURRENT_DATE_STR and movie_date not in dates:
            dates.append(movie_date)

    dates.sort()
    dates = dates[:9]
    n = len(dates)

    print("영화예매를 선택하셨습니다. 아래는 예매 가능한 날짜 리스트입니다.")
    if n == 0:
        info("상영이 예정된 영화가 없습니다.")
        return None

    for i, d in enumerate(dates, start=1):
        print(f"{i}) {d}")
    print("0) 뒤로 가기")

    while True:
        s = input("원하는 날짜의 번호를 입력해주세요 : ").strip()
        if not re.fullmatch(r"\d", s or "") or re.search(r"[A-Za-z]", s or ""):
            print("올바르지 않은 입력입니다. 원하는 날짜의 번호만 입력하세요.")
            continue
        num = int(s)
        if not (0 <= num <= n):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue
        if num == 0:
            return None
        return dates[num - 1]

def select_movie(selected_date: str) -> dict | None:
    """
    6.4.2 영화 선택 — 입력받은 날짜의 영화를 시간순으로 제시하고 선택
    """
    movie_path = home_path() / MOVIE_FILE
    lines = movie_path.read_text(encoding="utf-8").splitlines()

    movies: list[dict] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("/")
        if len(parts) < 5:
            continue
        movie_id, title, date_str, time_str, seat_vec = parts
        if date_str.strip() == selected_date:
            movies.append({
                "id": movie_id.strip(),
                "title": title.strip(),
                "date": date_str.strip(),
                "time": time_str.strip(),
                "seats": ast.literal_eval(seat_vec.strip()),
            })

    def sort_key(m: dict) -> str:
        return m["time"].split("-")[0]
    movies.sort(key=sort_key)
    n = len(movies)

    print(f"{selected_date}의 상영시간표입니다.")
    if n == 0:
        info("해당 날짜에는 상영 중인 영화가 없습니다.")
        return None

    for i, m in enumerate(movies, start=1):
        print(f"{i}) {m['date']} {m['time']} | {m['title']}")
    print("0) 뒤로 가기")

    while True:
        s = input("원하는 영화의 번호를 입력해주세요 : ").strip()
        if not re.fullmatch(r"\d", s or "") or re.search(r"[A-Za-z]", s):
            print("올바르지 않은 입력입니다. 원하는 영화의 번호만 입력해주세요.")
            continue
        num = int(s)
        if not (0 <= num <= n):
            print("해당 번호의 영화가 존재하지 않습니다. 다시 입력해주세요.")
            continue
        if num == 0:
            return None
        return movies[num - 1]

def input_people(selected_movie: dict) -> int | None:
    """6.4.3 인원 수 입력 — 최대 4명, 0이면 이전 단계로"""
    movie_date = selected_movie["date"]
    movie_time = selected_movie["time"]
    movie_title = selected_movie["title"]

    while True:
        s = input(f"{movie_date} {movie_time} | 〈{movie_title}〉를 선택하셨습니다. 인원 수를 입력해주세요 (최대 4명): ").strip()
        if not re.fullmatch(r"\d", s or "") or re.search(r"[A-Za-z]", s):
            print("올바르지 않은 입력입니다. 한 자리 숫자만 입력하세요.")
            continue
        n = int(s)
        if not (0 <= n <= 4):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue
        if n == 0:
            return None
        return n

def finalize_booking(selected_movie: dict, chosen_seats: list[str], student_id: str,
                     movie_path: Path, booking_path: Path) -> None:
    movie_id = selected_movie["id"]
    # 이번 예매의 좌석 벡터 만들기 (내가 선택한 좌석만 1)
    new_booking_vector = [0] * 25
    for seat in chosen_seats:
        row_idx = ROWS.index(seat[0])
        col_idx = int(seat[1]) - 1
        new_booking_vector[row_idx * 5 + col_idx] = 1

    # movie-schedule.txt 업데이트 (기존 1 유지 + 새 1 추가)
    lines = movie_path.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    for line in lines:
        parts = line.strip().split("/")
        if len(parts) < 5:
            updated_lines.append(line)
            continue
        movie_id_in_file = parts[0].strip()
        if movie_id_in_file == movie_id:
            seats = ast.literal_eval(parts[-1])
            for i in range(25):
                seats[i] = 1 if (seats[i] == 1 or new_booking_vector[i] == 1) else 0
            parts[-1] = "[" + ",".join(map(str, seats)) + "]"
            updated_line = "/".join(parts)
            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)
    movie_path.write_text("\n".join(updated_lines), encoding="utf-8")

    # booking-info.txt에 새로운 예매 레코드 추가
    with open(booking_path, "a+", encoding="utf-8") as f:
        f.seek(0)
        is_empty = (f.read().strip() == "")
        booking_vec_str = ",".join(map(str, new_booking_vector))
        if is_empty:
            f.write(f"{student_id}/{movie_id}/[{booking_vec_str}]")
        else:
            f.write(f"\n{student_id}/{movie_id}/[{booking_vec_str}]")

def input_seats(selected_movie: dict, n: int) -> bool:
    """
    6.4.4 좌석 입력 — 좌석 문법/예매 가능 여부/중복 검사 후 선택 처리
    """
    seat_vector = selected_movie["seats"]
    seat_buffer = create_seat_buffer(seat_vector)
    print_seat_board(seat_buffer)
    print()

    chosen_seats: list[str] = []
    k = 0
    while k < n:
        s = input(f"{k + 1}번째로 예매할 좌석을 입력하세요. (예:A1): ").strip().upper()
        if not re.fullmatch(r"[A-E][1-5]", s) or re.search(r"[가-힣]", s):
            print("올바르지 않은 입력입니다.")
            continue
        if seat_buffer[s] == 1:
            print("이미 예매된 좌석입니다.")
            continue
        if s in chosen_seats:
            print("동일 좌석 중복 선택은 불가능합니다.")
            continue
        seat_buffer[s] = 2
        chosen_seats.append(s)
        k += 1
        if k < n:
            print()
            print_seat_board(seat_buffer)
            print()
            continue
        else:
            movie_path = home_path() / MOVIE_FILE
            booking_path = home_path() / BOOKING_FILE
            finalize_booking(
                selected_movie=selected_movie,
                chosen_seats=chosen_seats,
                student_id=LOGGED_IN_SID,
                movie_path=movie_path,
                booking_path=booking_path,
            )
            print(f"{', '.join(chosen_seats)} 자리 예매가 완료되었습니다. 주 프롬프트로 돌아갑니다.")
            return True

def menu1() -> None:
    movie_path = home_path() / MOVIE_FILE
    student_path = home_path() / STUDENT_FILE
    booking_path = home_path() / BOOKING_FILE

    if LOGGED_IN_SID is None:
        error("로그인 정보가 없습니다. 주 프롬프트로 돌아갑니다.")
        return

    selected_date = select_date()
    if selected_date is None:
        return

    selected_movie = select_movie(selected_date)
    if selected_movie is None:
        return menu1()

    num_people = input_people(selected_movie)
    if num_people is None:
        return menu1()

    seat_input_success = input_seats(selected_movie, num_people)
    if not seat_input_success:
        return menu1()

    # 예매 후 데이터 재검증
    _ = load_and_validate_students(student_path)
    validate_movie_file(movie_path)
    validate_booking_syntax(booking_path)
    validate_all_booking_rules()
    prune_zero_seat_bookings(booking_path)


# ===== menu2: 예매 내역 조회 =====
def get_movie_details() -> dict[str, dict]:
    movie_path = home_path() / MOVIE_FILE
    lines = movie_path.read_text(encoding="utf-8").splitlines()
    details: dict[str, dict] = {}
    for line in lines:
        if not line.strip():
            continue
        parts = line.split('/')
        if len(parts) == 5:
            movie_id = parts[0].strip()
            title = parts[1].strip()
            date_str = parts[2].strip()
            time_str = parts[3].strip()
            details[movie_id] = {"title": title, "date": date_str, "time": time_str}
    return details

def vector_to_seats(vector: list[int]) -> list[str]:
    booked_seats: list[str] = []
    for i, status in enumerate(vector):
        if status == 1:
            row = ROWS[i // 5]
            col = COLS[i % 5]
            booked_seats.append(f"{row}{col}")
    return booked_seats

def menu2() -> None:
    """
    6.3.2 예매 내역 조회 — 현재 로그인 사용자의 '지나가지 않은' 예매 내역 출력
    """
    if not LOGGED_IN_SID:
        error("로그인 정보가 없습니다. 먼저 로그인해주세요.")
        return
    if not CURRENT_DATE_STR:
        error("가상 현재 날짜가 설정되지 않았습니다.")
        return
    booking_path = home_path() / BOOKING_FILE
    movie_details = get_movie_details()
    try:
        lines = booking_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        error(f"'{BOOKING_FILE}' 파일을 찾을 수 없습니다.")
        return
    user_bookings: list[dict] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split('/')
        if len(parts) == 3 and parts[0].strip() == LOGGED_IN_SID:
            movie_id = parts[1].strip()
            if movie_id not in movie_details:
                continue
            movie_info = movie_details[movie_id]
            movie_date = movie_info["date"]
            if movie_date < CURRENT_DATE_STR:
                continue
            vector_str = parts[2].strip()
            seat_vector = ast.literal_eval(vector_str)
            user_bookings.append({
                "title": movie_info["title"],
                "date": movie_date,
                "time": movie_info["time"],
                "seats": vector_to_seats(seat_vector),
            })
    print(f"\n{LOGGED_IN_SID} 님의 예매 내역입니다.")
    if not user_bookings:
        print(f"{LOGGED_IN_SID} 님의 예매 내역이 존재하지 않습니다. 주 프롬프트로 돌아갑니다.")
    else:
        user_bookings.sort(key=lambda b: (b['date'], b['time']))
        for i, booking in enumerate(user_bookings, 1):
            seat_list_str = ", ".join(booking["seats"])
            print(f"{i}) {booking['date']} {booking['time']} | {booking['title']} | 좌석: {seat_list_str}")
    print("주 프롬프트로 돌아갑니다.")


# ===== menu3: 예매 취소 =====
def load_records(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()

def parse_movie_record(line: str) -> dict:
    uid, title, ddate, ttime, seats = line.split("/", 4)
    return {
        "uid": uid.strip(),
        "title": title.strip(),
        "date": ddate.strip(),
        "time": ttime.strip(),
        "seats": ast.literal_eval(seats.strip()),
    }

def parse_booking_record(line: str) -> dict:
    sid, uid, seats = line.split("/", 2)
    return {"sid": sid.strip(), "uid": uid.strip(), "seats": ast.literal_eval(seats.strip())}

def save_records(path: Path, records: list[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for i, line in enumerate(records):
            line = line.strip()
            if i < len(records) - 1:
                f.write(line + "\n")
            else:
                f.write(line)

def select_cancelation(student_id: str) -> dict | None:
    if CURRENT_DATE_STR is None:
        error("내부 현재 날짜가 설정되어 있지 않습니다.")
        return None
    booking_path = home_path() / BOOKING_FILE
    movie_path = home_path() / MOVIE_FILE
    booking_lines = booking_path.read_text(encoding="utf-8").splitlines()
    movie_lines = movie_path.read_text(encoding="utf-8").splitlines()

    bookings: list[dict] = []
    for line in booking_lines:
        if not line.strip():
            continue
        parts = line.split("/", 2)
        if len(parts) < 3:
            continue
        student_who_booked, movie_id, seat_vec = parts
        movie_date = movie_id[0:4] + "-" + movie_id[4:6] + "-" + movie_id[6:8]
        if student_id == student_who_booked and movie_date > CURRENT_DATE_STR:
            for mline in movie_lines:
                if movie_id in mline:
                    pm = parse_movie_record(mline)
                    bookings.append({
                        "movie_id": movie_id.strip(),
                        "seats": ast.literal_eval(seat_vec.strip()),
                        "title": pm["title"],
                        "date": pm["date"],
                        "time": pm["time"],
                    })
                    break
    if not bookings:
        info(f"{student_id}님의 예매 내역이 존재하지 않습니다. 주 프롬프트로 돌아갑니다.")
        return None
    bookings.sort(key=lambda x: x["movie_id"])[:9]
    n = len(bookings)
    info(f"{student_id}님의 예매 내역입니다.")
    seat_names = [f"{row}{col}" for row in "ABCDE" for col in range(1, 6)]
    for i, d in enumerate(bookings, start=1):
        booked = [seat_names[idx] for idx, v in enumerate(d['seats']) if v == 1]
        seat_str = " ".join(booked) if booked else "(예매된 좌석 없음)"
        print(f"{i}) {d['date']} {d['time']} | {d['title']} | {seat_str}")
    print("0) 뒤로 가기")
    while True:
        s = input("예매를 취소할 내역을 선택해주세요. (번호로 입력) : ").strip()
        if not re.fullmatch(r"\d", s):
            print("올바르지 않은 입력입니다. 취소할 내역의 번호만 입력하세요.")
            continue
        num = int(s)
        if not (0 <= num <= n):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue
        if num == 0:
            return None
        return bookings[num - 1]

def confirm_cancelation(selected_booking: dict) -> None:
    movie_path = home_path() / MOVIE_FILE
    booking_path = home_path() / BOOKING_FILE

    seat_names = [f"{row}{col}" for row in "ABCDE" for col in range(1, 6)]
    seats = selected_booking.get('seats', [])
    if not seats:
        print("(예매된 좌석 없음)")
        return
    booked = [seat_names[idx] for idx, v in enumerate(seats) if v == 1]
    seat_str = " ".join(booked) if booked else "(예매된 좌석 없음)"
    n = input(f"{selected_booking['date']} {selected_booking['time']} | {selected_booking['title']} | {seat_str}의 예매를 취소하겠습니까? (Y/N) : ")
    if n == 'Y':
        booking_lines = booking_path.read_text(encoding="utf-8").splitlines()
        movie_lines = movie_path.read_text(encoding="utf-8").splitlines()
        new_booking_lines: list[str] = []
        for line in booking_lines:
            if not line.strip():
                continue
            parts = line.split("/")
            if len(parts) < 3:
                continue
            student_who_booked, movie_id, seat_vec = parts
            if (student_who_booked == LOGGED_IN_SID and 
                movie_id == selected_booking['movie_id'] and 
                ast.literal_eval(seat_vec.strip()) == selected_booking['seats']):
                continue
            new_booking_lines.append(line)
        new_movie_lines: list[str] = []
        for line in movie_lines:
            if not line.strip():
                continue
            parts = line.split("/", 4)
            if len(parts) < 5:
                continue
            uid, title, ddate, ttime, seats = parts
            if uid == selected_booking['movie_id']:
                current_seats = ast.literal_eval(seats.strip())
                restored_seats = [max(0, cs - ss) for cs, ss in zip(current_seats, selected_booking['seats'])]
                seat_str2 = "[" + ",".join(map(str, restored_seats)) + "]"
                new_line = f"{uid}/{title}/{ddate}/{ttime}/{seat_str2}"
                new_movie_lines.append(new_line)
            else:
                new_movie_lines.append(line)
        save_records(booking_path, new_booking_lines)
        save_records(movie_path, new_movie_lines)
        info("예매가 취소되었습니다.")
    else:
        menu3()
        return

def menu3() -> None:
    movie_path = home_path() / MOVIE_FILE
    student_path = home_path() / STUDENT_FILE
    booking_path = home_path() / BOOKING_FILE
    if LOGGED_IN_SID is None:
        error("로그인 정보가 없습니다. 주 프롬프트로 돌아갑니다.")
        return
    selected_cancelation = select_cancelation(LOGGED_IN_SID)
    if selected_cancelation is None:
        return
    confirm_cancelation(selected_cancelation)
    _ = load_and_validate_students(student_path)
    validate_movie_file(movie_path)
    validate_booking_syntax(booking_path)
    validate_all_booking_rules()
    prune_zero_seat_bookings(booking_path)


# ===== menu4: 상영 시간표 조회 =====
def menu4() -> None:
    """
    6.3.4 상영 시간표 조회 — 현재 날짜 이후 상영 시간표 출력
    """
    if not CURRENT_DATE_STR:
        error("가상 현재 날짜가 설정되지 않았습니다. 프로그램을 다시 시작해주세요.")
        return
    movie_path = home_path() / MOVIE_FILE
    try:
        lines = movie_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        error(f"'{MOVIE_FILE}' 파일을 찾을 수 없습니다.")
        return
    available_movies: list[dict] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split('/')
        if len(parts) == 5:
            movie_date = parts[2].strip()
            if movie_date < CURRENT_DATE_STR:
                continue
            available_movies.append({
                "date": movie_date,
                "time": parts[3].strip(),
                "title": parts[1].strip(),
            })
    print(f"상영시간표 조회를 선택하셨습니다. 현재 조회 가능한 모든 상영 시간표를 출력합니다.")
    if not available_movies:
        print("상영이 예정된 영화가 없습니다.")
    else:
        available_movies.sort(key=lambda m: (m['date'], m['time']))
        for i, movie in enumerate(available_movies, 1):
            print(f"{i}) {movie['date']} {movie['time']} | {movie['title']}")
    print("모든 상영 시간표 출력이 완료되었습니다. 주 프롬프트로 돌아갑니다.")

# ---------------------------------------------------------------
# 주 프롬프트(6.3) & 메뉴 디스패치
# ---------------------------------------------------------------
def show_main_menu() -> None:
    print()
    print("원하는 동작에 해당하는 번호를 입력하세요.")
    print("1) 영화 예매")
    print("2) 예매 내역 조회")
    print("3) 예매 취소")
    print("4) 상영 시간표 조회")
    print("0) 종료")


def dispatch_menu(choice: str) -> None:
    """동일 파일 내의 menu1~menu4 함수를 직접 호출."""
    mapping = {
        "1": menu1,
        "2": menu2,
        "3": menu3,
        "4": menu4,
    }
    func = mapping.get(choice)
    if func is None:
        error("잘못된 메뉴 선택입니다.")
        return
    try:
        func()
    except SystemExit:
        raise
    except Exception as e:
        error(f"메뉴 실행 중 예외가 발생했습니다: {e}")


def main_prompt_loop() -> None:
    """6.3 주 프롬프트 — 입력 검증 및 분기"""
    while True:
        show_main_menu()
        s = input("")

        # 문법 형식: 숫자만의 길이 1
        if not re.fullmatch(r"\d", s or ""):
            info("올바르지 않은 입력입니다. 원하는 동작에 해당하는 번호만 입력하세요.")
            continue

        # 의미 규칙: {1,2,3,4,0}
        if s not in {"1", "2", "3", "4", "0"}:
            info("범위 밖의 입력입니다. 다시 입력해주세요.")
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

    # 0-4) 예매 데이터 파일 무결성 검사(의미 규칙)
    validate_all_booking_rules()
    
    # 0-5) 좌석 예약 벡터가 모두 0인 예매 레코드 제거(경고 후 삭제)
    prune_zero_seat_bookings(booking_path)

    

    # 1) 6.1 — 날짜 입력
    CURRENT_DATE_STR = prompt_input_date()  # 내부 현재 날짜 확정

    # 2) 6.2 — 로그인 플로우
    while True:
        sid = prompt_student_id()  # 6.2.1
        if not prompt_login_intent(sid):  # 6.2.2 (부정이면 학번 입력 재시작)
            continue

        if sid in students:  # 기존 회원 → 6.2.3
            ok = prompt_password_existing(students[sid])
            if not ok:
                # 의미 규칙 위배(비밀번호 불일치) → 6.2.1로 되돌아감
                continue
            # 정상 로그인
            LOGGED_IN_SID = sid
            info(f"{LOGGED_IN_SID} 님 환영합니다.")
            break
        else:
            # 신규 회원 → 6.2.4
            prompt_password_new(student_path, sid, students)
            LOGGED_IN_SID = sid
            info(f"회원가입되었습니다. {LOGGED_IN_SID} 님 환영합니다.")
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
