#!/usr/bin/env python3
"""2024년 전체를 하루씩 나눠서 크롤링 (중복 없이)"""
import requests
import sqlite3
import os
from datetime import datetime, timedelta
import time

# DB 초기화
db_name = 'notam_2024_clean.db'
if os.path.exists(db_name):
    os.remove(db_name)
    print(f"[INFO] Removed old {db_name}")

conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# 테이블 생성 (UNIQUE 제약으로 중복 자동 제거)
cursor.execute('''
    CREATE TABLE notams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notam_number TEXT,
        a_location TEXT,
        b_start_time TEXT,
        c_end_time TEXT,
        d_schedule TEXT,
        e_text TEXT,
        f_lower_limit TEXT,
        g_upper_limit TEXT,
        collected_at TEXT,
        q_code TEXT,
        series_type TEXT,
        full_text TEXT,
        crawl_date TEXT,
        UNIQUE(notam_number, a_location, b_start_time, c_end_time)
    )
''')
conn.commit()

url = "https://aim.koca.go.kr/xNotam/searchAllNotam.do"
session = requests.Session()

# 2024년 전체 (366일 - 윤년)
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)

total_days = (end_date - start_date).days + 1
print("=" * 80)
print(f"Crawling 2024 (365 days) - Day by day")
print("=" * 80)

total_collected = 0
total_inserted = 0
total_duplicates = 0
current_day = start_date

for day_num in range(total_days):
    current_day = start_date + timedelta(days=day_num)
    date_str = current_day.strftime('%Y-%m-%d')
    
    # 국내 + 국제 둘 다
    for data_source in ['D', 'I']:
        source_name = 'Domestic' if data_source == 'D' else 'International'
        
        payload = {
            'sch_inorout': data_source,
            'sch_airport': 'RKSI,RKSS,RKPC,RKTN,RKTU,RKJJ,RKJB,RKNY,RKPU,RKPK,RKPS,RKSM,RKTH,RKTL,RKJY,RKNW,RKPE,RKSO,RKJK',
            'sch_from_date': date_str,
            'sch_from_time': '0000',
            'sch_to_date': date_str,
            'sch_to_time': '2359',
            'sch_series_type': 'A,C,D,E,G,Z,SNOWTAM',
            'sch_fir': '',
            'ibsheetPageNo': '1',
            'ibsheetRowPerPage': '100'
        }
        
        try:
            response = session.post(url, data=payload, timeout=30)
            data = response.json()
            
            if 'DATA' not in data or not data['DATA']:
                continue
            
            count = len(data['DATA'])
            total_collected += count
            
            inserted = 0
            duplicates = 0
            
            for item in data['DATA']:
                notam_no = item.get('NOTAM_NO', '')
                location = item.get('LOCATION', '')
                start_time = item.get('START_TIME', '')
                end_time = item.get('END_TIME', '')
                e_text = item.get('E', '')
                f_lower = item.get('F', '')
                g_upper = item.get('G', '')
                q_code = item.get('Q_CODE', '')
                series = item.get('SERIES', '')
                full_text = item.get('FULL_TEXT', '')
                
                try:
                    cursor.execute('''
                        INSERT INTO notams
                        (notam_number, a_location, b_start_time, c_end_time,
                         d_schedule, e_text, f_lower_limit, g_upper_limit,
                         collected_at, q_code, series_type, full_text, crawl_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (notam_no, location, start_time, end_time, '',
                          e_text, f_lower, g_upper, datetime.now().isoformat(),
                          q_code, series, full_text, date_str))
                    inserted += 1
                except sqlite3.IntegrityError:
                    duplicates += 1
            
            conn.commit()
            total_inserted += inserted
            total_duplicates += duplicates
            
            if count > 0:
                print(f"[{day_num+1:3d}/{total_days}] {date_str} {source_name:13s}: {count:3d} collected, {inserted:3d} inserted, {duplicates:3d} dup | Total: {total_inserted:,}")
            
        except Exception as e:
            print(f"[{day_num+1:3d}/{total_days}] {date_str} {source_name}: ERROR - {e}")
        
        time.sleep(0.2)  # API 부하 방지

conn.close()

print("\n" + "=" * 80)
print("COMPLETE!")
print("=" * 80)
print(f"Total collected: {total_collected:,}")
print(f"Total inserted: {total_inserted:,}")
print(f"Total duplicates: {total_duplicates:,}")
print(f"Database: {db_name}")
print("=" * 80)
