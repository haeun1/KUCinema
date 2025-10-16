import os
import re
import ast
import sys
from datetime import datetime
from KUCinema import MOVIE_FILE,BOOKING_FILE,STUDENT_FILE, info, error, home_path, validate_all_booking_rules,load_and_validate_students,validate_movie_file,validate_booking_syntax,prune_zero_seat_bookings
import core
from collections import defaultdict

#HOME = os.path.expanduser("~")
#BOOKING_FILE = os.path.join(HOME, "booking-info.txt")
#MOVIE_FILE = os.path.join(HOME, "movie-schedule.txt")


def load_records(path) -> None:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines

def parse_movie_record(line) -> None:
    uid, title, date, time, seats = line.split("/", 4)
    return {
        "uid": uid.strip(),
        "title": title.strip(),
        "date": date.strip(),
        "time": time.strip(),
        "seats": ast.literal_eval(seats.strip())
    }

def parse_booking_record(line) -> None:
    sid, uid, seats = line.split("/", 2)
    return {
        "sid": sid.strip(),
        "uid": uid.strip(),
        "seats": ast.literal_eval(seats.strip())
    }

def save_records(path, records) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for i, line in enumerate(records):
            line = line.strip()
            if i < len(records) - 1:
                f.write(line + "\n")
            else:
                f.write(line)
# ---------------------------------------------------------------
# 6.6.1 취소 대상 선택
# ---------------------------------------------------------------
def select_cancelation(student_id) -> dict | None:
    """
    6.6.1 날짜 선택
    - 예매 데이터 파일에서 현재 로그인한 학번, 현재 날짜 이후의 예매 내역을 출력
    - 정상 입력 시 예매 정보를 반환
    - '0' 입력 시 None 반환 (주 프롬프트 복귀)
    """
    
    if core.CURRENT_DATE_STR is None:
        error("내부 현재 날짜가 설정되어 있지 않습니다.")
        return None
    
    # 예매 데이터 파일, 영화 데이터 파일 읽기
    booking_path = home_path() / BOOKING_FILE
    movie_path = home_path() / MOVIE_FILE
    booking_lines = booking_path.read_text(encoding="utf-8").splitlines()
    movie_lines = movie_path.read_text(encoding="utf-8").splitlines()

    #print(booking_lines[0:])
    # 현재 로그인한 학번, 현재 날짜 이후의 예매 내역 추출
    bookings = []
    for line in booking_lines:
        if not line.strip():
            continue
        parts = line.split("/", 2)
        if len(parts) < 3:
            continue
        student_who_booked, movie_id, seat_vec = parts
        movie_date = movie_id[0:4] + "-" + movie_id[4:6] + "-" + movie_id[6:8]
        if student_id == student_who_booked and movie_date > core.CURRENT_DATE_STR:
            for mline in movie_lines:
                if movie_id in mline:
                    bookings.append({
                        "movie_id" : movie_id.strip(),
                        "seats" : ast.literal_eval(seat_vec.strip()),
                        "title": parse_movie_record(mline)["title"],
                        "date": parse_movie_record(mline)["date"],
                        "time": parse_movie_record(mline)["time"]
                    })
                    break
    
    # 예매 내역이 없으면 None 반환
    if not bookings:
        info(f"{student_id}님의 예매 내역이 존재하지 않습니다. 주 프롬프트로 돌아갑니다.")
        return None
    
    # 예매 내역 출력 (최대 9개)
    bookings.sort(key=lambda x: x["movie_id"])
    bookings = bookings[:9]
    n = len(bookings)
    info(f"{student_id}님의 예매 내역입니다.")

    # 출력 로직
    seat_names = [f"{row}{col}" for row in "ABCDE" for col in range(1, 6)]
    for i, d in enumerate(bookings, start=1):
        # 좌석 벡터에서 1인 것만 골라 좌석 이름으로 변환
        booked = [seat_names[idx] for idx, v in enumerate(d['seats']) if v == 1]
        seat_str = " ".join(booked) if booked else "(예매된 좌석 없음)"
    
        print(f"{i}) {d['date']} {d['time']} | {d['title']} | {seat_str}")

    print("0) 뒤로 가기")


    # 입력 로직
    while True:
        s = input("예매를 취소할 내역을 선택해주세요. (번호로 입력) : ").strip()

        # --- 문법 형식 위배 ---
        if not re.fullmatch(r"\d", s):
            print("올바르지 않은 입력입니다. 취소할 내역의 번호만 입력하세요.")
            continue

        num = int(s)

        # --- 의미 규칙 위배 ---
        if not (0 <= num <= n):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue

        # --- 정상 입력 ---
        if num == 0:
            # 주 프롬프트로 복귀
            return None
        else:
            # 선택한 예매 정보 반환
            return bookings[num - 1]

# ---------------------------------------------------------------
# 6.6.2 취소 최종 확인
# ---------------------------------------------------------------
def confirm_cancelation(selected_booking: dict) -> None:    
    """
    6.6.2 취소 최종 확인
    - Y 밖의 모든 입력은 N으로 간주
    - Y 입력 시 예매 데이터 파일, 영화 데이터 파일 수정, 6.6.1 재실행
    - N 입력 시 6.6.1 재실행
    """

    movie_path = home_path() / MOVIE_FILE
    student_path = home_path() / STUDENT_FILE
    booking_path = home_path() / BOOKING_FILE

    seat_names = [f"{row}{col}" for row in "ABCDE" for col in range(1, 6)]
    seat_str = ""
    seats = selected_booking.get('seats', [])
    if not seats:
        print("(예매된 좌석 없음)")
        return

    booked = [seat_names[idx] for idx, v in enumerate(seats) if v == 1]
    seat_str = " ".join(booked) if booked else "(예매된 좌석 없음)"

    n = input(f"{selected_booking['date']} {selected_booking['time']} | {selected_booking['title']} | {seat_str}의 예매를 취소하겠습니까? (Y/N) : ")

    if n == 'Y':
        # 예매 데이터 파일, 영화 데이터 파일 읽기
        booking_path = home_path() / BOOKING_FILE
        movie_path = home_path() / MOVIE_FILE
        booking_lines = booking_path.read_text(encoding="utf-8").splitlines()
        movie_lines = movie_path.read_text(encoding="utf-8").splitlines()

        # 예매 데이터 파일에서 해당 예매 정보 삭제
        new_booking_lines = []
        for line in booking_lines:
            if not line.strip():
                continue
            parts = line.split("/")
            if len(parts) < 3:
                continue
            student_who_booked, movie_id, seat_vec = parts
            if (student_who_booked == core.LOGGED_IN_SID and 
                movie_id == selected_booking['movie_id'] and 
                ast.literal_eval(seat_vec.strip()) == selected_booking['seats']):
                continue  # 이 줄은 삭제
            new_booking_lines.append(line)
        
        # 영화 데이터 파일에서 해당 좌석 벡터 복원
        new_movie_lines = []
        for line in movie_lines:
            if not line.strip():
                continue
            parts = line.split("/", 4)
            if len(parts) < 5:
                continue
            uid, title, date, time, seats = parts
            if uid == selected_booking['movie_id']:
                current_seats = ast.literal_eval(seats.strip())
                restored_seats = [max(0, cs - ss) for cs, ss in zip(current_seats, selected_booking['seats'])]
                seat_str = "[" + ",".join(map(str, restored_seats)) + "]"
                new_line = f"{uid}/{title}/{date}/{time}/{seat_str}"
                new_movie_lines.append(new_line)
            else:
                new_movie_lines.append(line)
        
        # 변경된 내용을 파일에 저장
        save_records(booking_path, new_booking_lines)
        save_records(movie_path, new_movie_lines)

        info("예매가 취소되었습니다.")
    else:
        menu3()
        return
    # 0-1) 학생 파일 최소 무결성 검사
    students = load_and_validate_students(student_path)
    
    # 0-2) 영화 데이터 파일 무결성(문법+의미) 검사 — 위배 발견 즉시 종료
    validate_movie_file(movie_path)

    # 0-3) 예매 데이터 파일 문법 검사 — 위배 행 전부 출력 후 종료
    validate_booking_syntax(booking_path)

    # 예매 데이터 파일 무결성 검사(의미 규칙)
    validate_all_booking_rules()

    # 6.6.1 재실행
    menu3()


def menu3():

    movie_path = home_path() / MOVIE_FILE
    student_path = home_path() / STUDENT_FILE
    booking_path = home_path() / BOOKING_FILE

    if core.LOGGED_IN_SID is None:
        error("로그인 정보가 없습니다. 주 프롬프트로 돌아갑니다.")
        return
    
    # -------------------------------
    # 6.6.1 취소 대상 선택
    # -------------------------------
    selected_cancelation = select_cancelation(core.LOGGED_IN_SID)
    if selected_cancelation is None:
        return
    
    # -------------------------------
    # 6.6.2 취소 최종 확인
    # -------------------------------
    confirm_cancelation(selected_cancelation)

    # 0-1) 학생 파일 최소 무결성 검사
    students = load_and_validate_students(student_path)
    
    # 0-2) 영화 데이터 파일 무결성(문법+의미) 검사 — 위배 발견 즉시 종료
    validate_movie_file(movie_path)

    # 0-3) 예매 데이터 파일 문법 검사 — 위배 행 전부 출력 후 종료
    validate_booking_syntax(booking_path)

    # 예매 데이터 파일 무결성 검사(의미 규칙)
    validate_all_booking_rules()

    prune_zero_seat_bookings(booking_path)