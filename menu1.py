import re
import ast
from KUCinema import MOVIE_FILE,BOOKING_FILE, info, error, home_path
import core

# ---------------------------------------------------------------
# 6.4.1 날짜 선택
# ---------------------------------------------------------------
def select_date() -> str | None:
    """
    6.4.1 날짜 선택
    - 영화 데이터 파일에서 현재 날짜 이후의 상영 날짜를 제시하고 선택을 받음
    - 정상 입력 시 해당 날짜 문자열을 반환
    - '0' 입력 시 None 반환 (주 프롬프트 복귀)
    """

    if core.CURRENT_DATE_STR is None:
        error("내부 현재 날짜가 설정되어 있지 않습니다.")
        return None

    # 1️. 영화 데이터 파일 읽기
    movie_path = home_path() / MOVIE_FILE
    lines = movie_path.read_text(encoding="utf-8").splitlines()

    # 2️. 현재 날짜 이후 상영 날짜만 추출 (중복 제거)
    dates = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("/")
        if len(parts) < 5:
            continue
        _, _, movie_date, _, _ = parts
        if movie_date > core.CURRENT_DATE_STR and movie_date not in dates:
            dates.append(movie_date)

    # 3️. 날짜 정렬 및 최대 9개 제한
    dates.sort()
    dates = dates[:9]
    n = len(dates)

    # 4️. 출력 화면 구성
    print("영화예매를 선택하셨습니다. 아래는 예매 가능한 날짜 리스트입니다.")
    if n == 0:
        info("현재 날짜 이후 상영 예정 영화가 없습니다.")
        return None

    for i, d in enumerate(dates, start=1):
        print(f"{i}) {d}")
    print("0) 뒤로 가기")

    # 5️. 입력 로직
    while True:
        s = input("원하는 날짜의 번호를 입력해주세요 : ").strip()

        # --- 문법 형식 위배 ---
        if not re.fullmatch(r"\d", s or ""):
            print("올바르지 않은 입력입니다. 원하는 날짜의 번호만 입력하세요.")
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
            selected_date = dates[num - 1]
            return selected_date

# ---------------------------------------------------------------
# 6.4.2 영화 선택
# ---------------------------------------------------------------
def select_movie(selected_date: str) -> dict | None:
    """
    6.4.2 영화 선택
    - 입력받은 날짜에 상영 중인 모든 영화를 시간순으로 제시하고 선택을 받음
    - 정상 선택 시 영화 딕셔너리 반환
    - '0' 입력 시 None 반환 (6.4.1로 되돌아감)
    """
    movie_path = home_path() / MOVIE_FILE
    lines = movie_path.read_text(encoding="utf-8").splitlines()

    # 1️. 해당 날짜의 영화만 추출
    movies = []
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
                "seats": ast.literal_eval(seat_vec.strip())
            })

    # 2️. 시간순 정렬 (시작 시각 기준)
    def sort_key(m):  # "HH:MM-HH:MM"
        return m["time"].split("-")[0]
    movies.sort(key=sort_key)

    n = len(movies)

    # 3️. 출력
    print(f"{selected_date}의 상영시간표입니다.")
    if n == 0:
        info("해당 날짜에는 상영 중인 영화가 없습니다.")
        return None

    for i, m in enumerate(movies, start=1):
        print(f"{i}) {m['date']} {m['time']} | {m['title']}")
    print("0) 뒤로 가기")

    # 4️. 입력 루프
    while True:
        s = input("원하는 영화의 번호를 입력해주세요 : ").strip()

        # --- 문법 형식 위배 ---
        if not re.fullmatch(r"\d", s or ""):
            print("올바르지 않은 입력입니다. 원하는 영화의 번호만 입력해주세요.")
            continue

        num = int(s)

        # --- 의미 규칙 위배 ---
        if not (0 <= num <= n):
            print("해당 번호의 영화가 존재하지 않습니다. 다시 입력해주세요.")
            continue

        # --- 정상 입력 ---
        if num == 0:
            # 날짜 선택(6.4.1)으로 복귀
            return None
        else:
            selected_movie = movies[num - 1]
            return selected_movie

# ---------------------------------------------------------------
# 6.4.3 인원 수 입력
# ---------------------------------------------------------------
def input_people(selected_movie: dict) -> int | None:
    """
    6.4.3 인원 수 입력
    - 선택된 영화에 대해 인원 수(최대 4명)를 입력받음
    - 정상 입력 시 인원 수(int) 반환
    - '0' 입력 시 이전 단계(6.4.2 영화 선택)로 복귀 → None 반환
    """
    movie_date = selected_movie["date"]
    movie_time = selected_movie["time"]
    movie_title = selected_movie["title"]

    # 화면 출력
    print(f"{movie_date} {movie_time} | 〈{movie_title}〉를 선택하셨습니다. 인원 수를 입력해주세요 (최대 4명):")

    # 입력 루프
    while True:
        s = input("인원 수 입력 (0~4): ").strip()

        # --- 문법 형식 위배 ---
        if not re.fullmatch(r"\d", s or ""):
            print("올바르지 않은 입력입니다. 한 자리 숫자만 입력하세요.")
            continue

        n = int(s)

        # --- 의미 규칙 위배 ---
        if not (0 <= n <= 4):
            print("범위 밖의 입력입니다. 다시 입력해주세요.")
            continue

        # --- 정상 입력 ---
        if n == 0:
            # 6.4.2로 복귀
            return None
        else:
            # 6.4.4로 진행
            return n
# ---------------------------------------------------------------
# 6.4.4 좌석 선택 단계
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# 기본 좌석 설정
# ---------------------------------------------------------------
ROWS = ["A", "B", "C", "D", "E"]
COLS = [1, 2, 3, 4, 5]

# ---------------------------------------------------------------
# 좌석 벡터 → 버퍼 변환
# ---------------------------------------------------------------
def create_seat_buffer(seat_vector: list[int]) -> dict[str, int]:
    """
    영화의 좌석 유무 벡터(길이 25, 0/1)를 
    {'A1':0, 'A2':1, ..., 'E5':1} 형태로 변환
    """
    seat_buffer = {}
    idx = 0
    for row in ROWS:
        for col in COLS:
            seat_id = f"{row}{col}"
            seat_buffer[seat_id] = seat_vector[idx]
            idx += 1
    return seat_buffer


# ---------------------------------------------------------------
# 좌석표 출력 함수
# ---------------------------------------------------------------
def print_seat_board(seat_buffer: dict[str, int]) -> None:
    """
    좌석 버퍼를 기반으로 현재 좌석 상태를 콘솔에 시각화하여 출력
    - '□' : 예매 가능 (0)
    - '■' : 이미 예매됨 (1)
    - '*' : 이번 예매에서 방금 선택한 좌석 (2)
    """
    print("빈 사각형은 예매 가능한 좌석입니다.")
    print("   스크린")
    print("  ", " ".join(str(c) for c in COLS))

    for row in ROWS:
        line = [f"{row}"]
        for col in COLS:
            seat_id = f"{row}{col}"
            val = seat_buffer[seat_id]
            if val == 0:
                line.append("□")  # 예매 가능
            elif val == 1:
                line.append("■")  # 이미 예매됨
            elif val == 2:
                line.append("★")  # 현재 예매 중
        print(" ", " ".join(line))

# ---------------------------------------------------------------
# 파일 반영
# ---------------------------------------------------------------
def finalize_booking(selected_movie: dict, chosen_seats: list[str], student_id: str,
                     movie_path, booking_path) -> None:
    movie_id = selected_movie["id"]
    date = selected_movie["date"]
    time = selected_movie["time"]

    # 이번 예매의 좌석 벡터 만들기 (내가 선택한 좌석만 1)
    new_booking_vector = [0] * 25
    for seat in chosen_seats:
        row_idx = ROWS.index(seat[0])
        col_idx = int(seat[1]) - 1
        new_booking_vector[row_idx * 5 + col_idx] = 1

    # movie-schedule.txt 업데이트 (기존 1 유지 + 새 1 추가)
    lines = movie_path.read_text(encoding="utf-8").splitlines()
    updated_lines = []

    for line in lines:
        parts = line.strip().split("/")
        if len(parts) < 5:
            updated_lines.append(line)
            continue

        movie_id_in_file = parts[0].strip()
        if movie_id_in_file == movie_id:
            seats = ast.literal_eval(parts[-1])
            for i in range(25):
                # 기존이 1이면 그대로, 새로 선택된 좌석이면 1로 바꿈
                seats[i] = 1 if (seats[i] == 1 or new_booking_vector[i] == 1) else 0
            parts[-1] = "[" + ",".join(map(str, seats)) + "]"
            updated_line = "/".join(parts)
            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)

    # 파일 덮어쓰기
    movie_path.write_text("\n".join(updated_lines), encoding="utf-8")

    # booking-info.txt에 새로운 예매 레코드 추가
    with open(booking_path, "a", encoding="utf-8") as f:
        booking_vec_str = ",".join(map(str, new_booking_vector))
        f.write(f"{student_id}/{movie_id}/{date}/{time}/[{booking_vec_str}]\n")

    print("예매 내역이 movie-schedule.txt 및 booking-info.txt에 성공적으로 반영되었습니다.")

def input_seats(selected_movie: dict, n: int) -> None:
    """
    6.4.4 좌석 입력
    - 입력받은 관람 인원(n)만큼 좌석을 한 명씩 입력받는다.
    - 좌석 문법, 예매 가능 여부, 중복 선택 검사 수행
    - 올바른 좌석 입력 시 버퍼에 반영하고 즉시 현황 재출력
    - 모든 인원 좌석 선택 완료 시 예매 데이터 파일 기록 후 주 프롬프트로 복귀 (기록 아직)
    """

    # 1️. 좌석 벡터 불러오기
    seat_vector = selected_movie["seats"]

    # 2️. 버퍼 생성
    seat_buffer = create_seat_buffer(seat_vector)

    # 3️. 초기 좌석 현황 출력
    print_seat_board(seat_buffer)
    print()

    # 4️. 선택 현황 초기화
    chosen_seats = []
    k = 0  # 현재까지 선택된 인원 수

    # 5️. 좌석 입력 루프
    while k < n:
        s = input(f"{k + 1}번째로 예매할 좌석을 입력하세요. (예:A1): ").strip().upper()

        # --- 문법 형식 위배 ---
        if not re.fullmatch(r"[A-E][1-5]", s):
            print("올바르지 않은 입력입니다.")
            continue

        # --- 의미 규칙 위배 --- 1. 이미 예매된 좌석 ---
        if seat_buffer[s] == 1:
            print("이미 예매된 좌석입니다.")
            continue

        # --- 의미 규칙 위배 --- 2. 동일 예매 흐름 내 중복 ---
        if s in chosen_seats:
            print("동일 좌석 중복 선택은 불가능합니다.")
            continue

         # --- 정상 입력 ---
        seat_buffer[s] = 2  # 선택한 좌석을 '예매 중'으로 표시
        chosen_seats.append(s)
        k += 1

        # --- 분기 ---
        if k < n:
            # 아직 모든 인원 좌석 미선택 - 좌석표 재출력
            print()
            print_seat_board(seat_buffer)
            print()
            continue
        else:
            # 모든 인원 좌석 선택 완료
            movie_path = home_path() / MOVIE_FILE
            booking_path = home_path() / BOOKING_FILE
            finalize_booking(
                selected_movie=selected_movie,
                chosen_seats=chosen_seats,
                student_id=core.LOGGED_IN_SID,
                movie_path=movie_path,
                booking_path=booking_path,
            )

            print(f"{', '.join(chosen_seats)} 자리 예매가 와료되었습니다. 주. 프롬프트로 돌아갑니다.")
            break

def menu1():
    if core.LOGGED_IN_SID is None:
        error("로그인 정보가 없습니다. 주 프롬프트로 돌아갑니다.")
        return

    # -------------------------------
    # 6.4.1 날짜 선택
    # -------------------------------
    selected_date = select_date()
    if selected_date is None:
        info("주 프롬프트로 돌아갑니다.")
        return

    # -------------------------------
    # 6.4.2 영화 선택
    # -------------------------------
    selected_movie = select_movie(selected_date)
    if selected_movie is None:
        # 날짜 선택으로 복귀
        return menu1()  

    # -------------------------------
    # 6.4.3 인원 수 입력
    # -------------------------------
    num_people = input_people(selected_movie)
    if num_people is None:
        # 영화 선택으로 복귀
        return menu1()

    # -------------------------------
    # 6.4.4 좌석 입력
    # -------------------------------
    input_seats(selected_movie, num_people)
    return

