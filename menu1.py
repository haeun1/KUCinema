import re
from KUCinema import CURRENT_DATE_STR, MOVIE_FILE, info, error, home_path

# ---------------------------------------------------------------
# 6.4.1 날짜 선택
# ---------------------------------------------------------------
def select_date() -> str | None:

    if CURRENT_DATE_STR is None:
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
        if movie_date > CURRENT_DATE_STR and movie_date not in dates:
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


def menu1():
    print("menu1")
    pass


