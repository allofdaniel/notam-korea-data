#!/usr/bin/env python3
"""페이지네이션 파라미터 테스트"""
import requests
from datetime import datetime, timedelta
import pytz

# API endpoint
url = "https://aim.koca.go.kr/xNotam/searchAllNotam.do"

# 기본 payload
base_payload = {
    'sch_inorout': 'D',
    'sch_airport': 'RKSI,RKSS,RKPC,RKTN,RKTU,RKJJ,RKJB,RKNY,RKPU,RKPK,RKPS,RKSM,RKTH,RKTL,RKJY,RKNW,RKPE,RKSO,RKJK',
    'sch_from_date': '2024-12-01',
    'sch_from_time': '0000',
    'sch_to_date': '2024-12-31',
    'sch_to_time': '2359',
    'sch_series_type': 'A,C,D,E,G,Z,SNOWTAM',
    'sch_fir': '',
    'ibsheetRowPerPage': '100'
}

session = requests.Session()

print("=" * 80)
print("Testing pagination parameters")
print("=" * 80)

# 테스트: ibsheetPageNo로 페이지 1,2의 첫번째 NOTAM이 다른지 확인
print("\nFetching page 1 and page 2 to compare...")

page1_data = []
page2_data = []

for page_num in [1, 2]:
    payload = base_payload.copy()
    payload['ibsheetPageNo'] = str(page_num)
    
    try:
        response = session.post(url, data=payload, timeout=30)
        data = response.json()
        
        if 'DATA' in data and data['DATA']:
            notam_list = [item.get('NOTAM_NO', 'N/A') for item in data['DATA'][:5]]
            
            if page_num == 1:
                page1_data = notam_list
                print(f"\nPage 1 first 5 NOTAMs: {notam_list}")
            else:
                page2_data = notam_list
                print(f"Page 2 first 5 NOTAMs: {notam_list}")
        else:
            print(f"Page {page_num}: No data")
    except Exception as e:
        print(f"Page {page_num}: Error - {e}")

# 비교
if page1_data and page2_data:
    if page1_data == page2_data:
        print("\n❌ PROBLEM: Page 1 and Page 2 have SAME data!")
        print("   Pagination is NOT working!")
    else:
        print("\n✅ OK: Page 1 and Page 2 have DIFFERENT data")
        print("   Pagination is working correctly")

print("\n" + "=" * 80)
