#!/usr/bin/env python3
"""작은 규모로 페이지네이션 테스트 - 최근 7일"""
import requests
from datetime import datetime, timedelta

url = "https://aim.koca.go.kr/xNotam/searchAllNotam.do"

# 최근 7일
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

payload = {
    'sch_inorout': 'D',
    'sch_airport': 'RKSI,RKSS,RKPC,RKTN,RKTU,RKJJ,RKJB,RKNY,RKPU,RKPK,RKPS,RKSM,RKTH,RKTL,RKJY,RKNW,RKPE,RKSO,RKJK',
    'sch_from_date': start_date.strftime('%Y-%m-%d'),
    'sch_from_time': '0000',
    'sch_to_date': end_date.strftime('%Y-%m-%d'),
    'sch_to_time': '2359',
    'sch_series_type': 'A,C,D,E,G,Z,SNOWTAM',
    'sch_fir': '',
    'ibsheetRowPerPage': '100'
}

print("=" * 80)
print(f"Test: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} (7 days)")
print("=" * 80)

session = requests.Session()
all_notams = []
page_samples = {}

for page in range(1, 6):
    payload['ibsheetPageNo'] = str(page)
    
    try:
        response = session.post(url, data=payload, timeout=30)
        data = response.json()
        
        if 'DATA' not in data or not data['DATA']:
            print(f"\nPage {page}: No more data")
            break
        
        count = len(data['DATA'])
        total = data.get('Total', 'N/A')
        
        sample = [item.get('NOTAM_NO', 'N/A') for item in data['DATA'][:3]]
        page_samples[page] = sample
        
        for item in data['DATA']:
            notam_no = item.get('NOTAM_NO', '')
            location = item.get('LOCATION', '')
            start_time = item.get('START_TIME', '')
            all_notams.append((notam_no, location, start_time))
        
        print(f"Page {page}: {count} records, Total={total}, Sample: {sample}")
        
    except Exception as e:
        print(f"Page {page}: Error - {e}")
        break

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)

print("\nPage sample comparison:")
for i in range(1, len(page_samples)):
    if i+1 in page_samples:
        same = page_samples[i] == page_samples[i+1]
        status = "SAME (BUG!)" if same else "DIFFERENT (OK)"
        print(f"  Page {i} vs {i+1}: {status}")
        if same:
            print(f"    Both: {page_samples[i]}")

total_collected = len(all_notams)
unique_notams = len(set(all_notams))
duplicates = total_collected - unique_notams

print(f"\nTotal collected: {total_collected}")
print(f"Unique NOTAMs: {unique_notams}")
print(f"Duplicates: {duplicates}")

if duplicates > 0:
    dup_rate = (duplicates / total_collected * 100) if total_collected > 0 else 0
    print(f"Duplicate rate: {dup_rate:.1f}%")
    print("\nWARNING: Pagination is NOT working!")
else:
    print("\nOK: Pagination is working correctly!")

print("=" * 80)
