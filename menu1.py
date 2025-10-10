import re
import ast
from KUCinema import MOVIE_FILE, info, error, home_path
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
        print(f">> {i}) {d}")
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
    print(f">> {selected_date}의 상영시간표입니다.")
    if n == 0:
        info("해당 날짜에는 상영 중인 영화가 없습니다.")
        return None

    for i, m in enumerate(movies, start=1):
        print(f">> {i}) {m['date']} {m['time']} | {m['title']}")
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


def menu1():
    print("menu1")
    """
    6.4 영화 예매 기능 전체 흐름 제어 함수
    날짜 선택(6.4.1) → 영화 선택(6.4.2) → 인원 수 입력(6.4.3) 순으로 실행.
    각 단계에서 '0' 입력 시 상위 단계로 복귀.
    """
    if core.LOGGED_IN_SID is None:
        error("로그인 정보가 없습니다. 주 프롬프트로 돌아갑니다.")
        return

    # -------------------------------
    # 6.4.1 날짜 선택
    # -------------------------------
    selected_date = select_date()
    if selected_date is None:
        info(">> 주 프롬프트로 돌아갑니다.")
        return

    # -------------------------------
    # 6.4.2 영화 선택
    # -------------------------------
    selected_movie = select_movie(selected_date)
    if selected_movie is None:
        # 날짜 선택으로 복귀
        return menu1()  # 사용자가 뒤로 가기를 선택했을 때

    # -------------------------------
    # 6.4.3 인원 수 입력
    # -------------------------------
    num_people = input_people(selected_movie)
    if num_people is None:
        # 영화 선택으로 복귀
        return menu1()

    # -------------------------------
    # 6.4.4 좌석 입력 (다음 단계에서 구현 예정)
    # -------------------------------
    info(f">> {num_people}명 좌석 선택 단계로 이동합니다. (6.4.4 좌석 입력 예정)")
    # TODO: implement input_seats(selected_movie, num_people)
    pass
    pass

