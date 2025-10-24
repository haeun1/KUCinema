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
    #hp = Path(os.path.expanduser("~")).resolve() # 홈 경로 반환
    # try:
    #     hp = Path(os.path.expanduser("~")).resolve()  # 홈 경로 반환
    # except Exception as e:
    #     error(f"홈 경로를 파악할 수 없습니다! 프로그램을 종료합니다. {e}")
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
    ans = input(f"{sid}님으로 로그인하시겠습니까? (Y/N) : ")
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
            core.LOGGED_IN_SID = sid
            core.CURRENT_DATE_STR = CURRENT_DATE_STR
            break
        else:
            # 신규 회원 → 6.2.4
            prompt_password_new(student_path, sid, students)
            LOGGED_IN_SID = sid
            info(f"회원가입되었습니다. {LOGGED_IN_SID} 님 환영합니다.")
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
