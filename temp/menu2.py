# 이건희가 해야해용
import ast
from KUCinema import MOVIE_FILE, BOOKING_FILE, info, error, home_path
import core

# 좌석 인덱스를 좌표(예: A1)로 변환하기 위한 상수
ROWS = ["A", "B", "C", "D", "E"]
COLS = [1, 2, 3, 4, 5]

def get_movie_details() -> dict[str, dict]:
    """
    movie-schedule.txt 파일을 읽어 각 영화의 상세 정보를 딕셔너리로 반환합니다.
    - Key: 영화 고유번호
    - Value: {'title': 제목, 'date': 날짜, 'time': 시간}
    """
    movie_path = home_path() / MOVIE_FILE
    lines = movie_path.read_text(encoding="utf-8").splitlines()
    
    details = {}
    for line in lines:
        if not line.strip():
            continue
        # movie-schedule.txt 형식: 고유번호/제목/날짜/시간/[벡터] (5개 필드)
        parts = line.split('/')
        if len(parts) == 5:
            movie_id = parts[0].strip()
            title = parts[1].strip()
            date_str = parts[2].strip()
            time_str = parts[3].strip()
            details[movie_id] = {"title": title, "date": date_str, "time": time_str}
            
    return details

def vector_to_seats(vector: list[int]) -> list[str]:
    """
    좌석 예약 벡터(길이 25)를 실제 좌석 번호 리스트로 변환합니다.
    """
    booked_seats = []
    for i, status in enumerate(vector):
        if status == 1:
            row = ROWS[i // 5]
            col = COLS[i % 5]
            booked_seats.append(f"{row}{col}")
    return booked_seats

def menu2():
    """
    6.3.2 예매 내역 조회
    - booking-info.txt에서 현재 로그인 사용자의 '지나가지 않은' 예매 내역을 찾아 출력합니다.
    - 영화 상세 정보(제목, 날짜, 시간)는 movie-schedule.txt를 참조합니다.
    """
    # 1. 로그인 및 현재 날짜 상태 확인
    if not core.LOGGED_IN_SID:
        error("로그인 정보가 없습니다. 먼저 로그인해주세요.")
        return
    if not core.CURRENT_DATE_STR:
        error("가상 현재 날짜가 설정되지 않았습니다.")
        return

    # 2. 필요한 데이터 파일 경로 설정
    booking_path = home_path() / BOOKING_FILE
    
    # 3. 모든 영화의 상세 정보 미리 가져오기
    movie_details = get_movie_details()
    
    # 4. booking-info.txt 파일 읽기
    try:
        lines = booking_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        error(f"'{BOOKING_FILE}' 파일을 찾을 수 없습니다.")
        return

    # 5. 현재 로그인한 사용자의 '유효한' 예매 내역 필터링
    user_bookings = []
    for line in lines:
        if not line.strip():
            continue
        
        parts = line.split('/')
        # booking-info.txt 형식: 학번/영화고유번호/[좌석예약벡터] (3개 필드)
        if len(parts) == 3 and parts[0].strip() == core.LOGGED_IN_SID:
            movie_id = parts[1].strip()
            
            # 영화 정보가 movie_details에 없으면 건너뜀 (무결성)
            if movie_id not in movie_details:
                continue
            
            movie_info = movie_details[movie_id]
            movie_date = movie_info["date"]
            
            # --- ✨ 지나간 예매 내역 필터링 ---
            if movie_date < core.CURRENT_DATE_STR:
                continue
            # ---------------------------------

            vector_str = parts[2].strip()
            seat_vector = ast.literal_eval(vector_str)
            
            user_bookings.append({
                "title": movie_info["title"],
                "date": movie_date,
                "time": movie_info["time"],
                "seats": vector_to_seats(seat_vector)
            })

    # 6. 결과 출력
    print(f"\n{core.LOGGED_IN_SID} 님의 예매 내역입니다.")
    if not user_bookings:
        print(f"{core.LOGGED_IN_SID} 님의 예매 내역이 존재하지 않습니다. 주 프롬프트로 돌아갑니다.")
    else:
        # 날짜와 시간 순으로 정렬하여 출력
        user_bookings.sort(key=lambda b: (b['date'], b['time']))
        for i, booking in enumerate(user_bookings, 1):
            seat_list_str = ", ".join(booking["seats"])
            print(f"{i}) {booking['date']} {booking['time']} | {booking['title']} | 좌석: {seat_list_str}")
    
    print("주 프롬프트로 돌아갑니다.")