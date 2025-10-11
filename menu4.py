#이건희가 해야해용
from KUCinema import MOVIE_FILE, info, error, home_path
import core

def menu4():
    """
    6.3.4 상영 시간표 조회
    - 가상 현재 날짜를 기준으로, 예매 가능한 모든 영화의 상영 시간표를
      movie-schedule.txt에서 읽어와 날짜와 시간순으로 출력합니다.
    """
    # 1. 가상 현재 날짜가 설정되었는지 확인
    if not core.CURRENT_DATE_STR:
        error("가상 현재 날짜가 설정되지 않았습니다. 프로그램을 다시 시작해주세요.")
        return

    # 2. 영화 데이터 파일 읽기
    movie_path = home_path() / MOVIE_FILE
    try:
        lines = movie_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        error(f"'{MOVIE_FILE}' 파일을 찾을 수 없습니다.")
        return

    # 3. 현재 날짜 이후의 상영 정보만 필터링
    available_movies = []
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.split('/')
        # movie-schedule.txt 형식: 고유번호/제목/날짜/시간/[벡터]
        if len(parts) == 5:
            movie_date = parts[2].strip()
            
            # 가상 현재 날짜보다 이전 날짜의 영화는 건너뜀
            if movie_date < core.CURRENT_DATE_STR:
                continue

            available_movies.append({
                "date": movie_date,
                "time": parts[3].strip(),
                "title": parts[1].strip()
            })

    # 4. 결과 출력
    print(f"\n--- 전체 상영 시간표 (기준일: {core.CURRENT_DATE_STR}) ---")
    if not available_movies:
        print("예매 가능한 상영 정보가 없습니다.")
    else:
        # 날짜와 시간 순으로 정렬하여 출력
        available_movies.sort(key=lambda m: (m['date'], m['time']))
        for i, movie in enumerate(available_movies, 1):
            print(f"{i}) {movie['date']} {movie['time']} | {movie['title']}")
            
    print("------------------------------------------")
    input("확인하셨으면 Enter 키를 누르세요...")



