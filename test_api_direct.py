"""API 직접 테스트 - 실제 응답 확인"""
import requests
import json
from datetime import datetime, timedelta

# API 엔드포인트
url = 'https://aim.koca.go.kr/xNotam/searchAllNotam.do'

# 현재 시간 (UTC)
utc_now = datetime.utcnow()
start_time = utc_now - timedelta(hours=24)

# 요청 페이로드
payload = {
    'sch_inorout': 'N',  # 국내선
    'sch_airport': 'RKSI,RKSS,RKPK,RKPC,RKPS,RKPU,RKSM,RKTH,RKPD,RKTL,RKNW,RKJK,RKJB,RKJY,RKJJ,RKTN,RKTU,RKNY',
    'sch_from_date': start_time.strftime('%Y-%m-%d'),
    'sch_from_time': start_time.strftime('%H%M'),
    'sch_to_date': utc_now.strftime('%Y-%m-%d'),
    'sch_to_time': utc_now.strftime('%H%M'),
    'sch_series': 'A,C,D,E,G,Z',
    'sch_snow_series': 'SNOWTAM',
    'sch_notam_no': '',
    'sch_elevation_min': '',
    'sch_elevation_max': '',
    'sch_qcode': '',
    'sch_fir': '',
    'sch_full_text': '',
    'sch_select': ''
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': 'https://aim.koca.go.kr',
    'Referer': 'https://aim.koca.go.kr/xNotam/?language=ko_KR'
}

print("API 요청 중...")
print(f"시작: {start_time.strftime('%Y-%m-%d %H:%M')}")
print(f"종료: {utc_now.strftime('%Y-%m-%d %H:%M')}")
print()

try:
    response = requests.post(url, data=payload, headers=headers, timeout=30)
    print(f"응답 코드: {response.status_code}")
    print(f"응답 길이: {len(response.text)} bytes")
    print()

    # 응답 내용 확인
    print("=== 응답 내용 (처음 500자) ===")
    print(response.text[:500])
    print()

    # JSON 파싱 시도
    try:
        data = json.loads(response.text)
        print("=== JSON 파싱 성공 ===")
        print(f"키: {list(data.keys())}")

        if 'DATA' in data:
            print(f"NOTAM 개수: {len(data['DATA'])}")
            if data['DATA']:
                print("\n첫 번째 NOTAM:")
                print(json.dumps(data['DATA'][0], indent=2, ensure_ascii=False))
        elif 'data' in data:
            print(f"NOTAM 개수: {len(data['data'])}")

    except json.JSONDecodeError:
        print("JSON 파싱 실패 - XML 또는 다른 형식일 수 있음")

except Exception as e:
    print(f"에러: {e}")
