#!/usr/bin/env python3
"""1년치 조회 후 페이지네이션 테스트"""
import requests

url = "https://aim.koca.go.kr/xNotam/searchAllNotam.do"

# 2024년 전체 조회
payload = {
    'sch_inorout': 'D',
    'sch_airport': 'RKSI,RKSS,RKPC,RKTN,RKTU,RKJJ,RKJB,RKNY,RKPU,RKPK,RKPS,RKSM,RKTH,RKTL,RKJY,RKNW,RKPE,RKSO,RKJK',
    'sch_from_date': '2024-01-01',
    'sch_from_time': '0000',
    'sch_to_date': '2024-12-31',
    'sch_to_time': '2359',
    'sch_series_type': 'A,C,D,E,G,Z,SNOWTAM',
    'sch_fir': '',
    'ibsheetRowPerPage': '100'
}

print("=" * 80)
print("Testing 2024 full year pagination")
print("=" * 80)

session = requests.Session()
page_data = {}

# 페이지 1-5 테스트
for page in range(1, 6):
    payload['ibsheetPageNo'] = str(page)
    
    try:
        response = session.post(url, data=payload, timeout=30)
        data = response.json()
        
        if 'DATA' not in data or not data['DATA']:
            print(f"\nPage {page}: No data")
            break
        
        count = len(data['DATA'])
        total = data.get('Total', 'N/A')
        
        # 처음 5개 NOTAM 번호
        sample = [item.get('NOTAM_NO', 'N/A') for item in data['DATA'][:5]]
        page_data[page] = sample
        
        print(f"Page {page}: {count} records, Total={total}")
        print(f"  Sample: {sample}")
        
    except Exception as e:
        print(f"Page {page}: Error - {e}")
        break

print("\n" + "=" * 80)
print("PAGINATION CHECK:")
print("=" * 80)

for i in range(1, len(page_data)):
    if i+1 in page_data:
        same = page_data[i] == page_data[i+1]
        if same:
            print(f"Page {i} vs {i+1}: SAME (pagination NOT working)")
        else:
            print(f"Page {i} vs {i+1}: DIFFERENT (pagination OK!)")

print("=" * 80)
