#!/usr/bin/env python3
"""완전한 NOTAM 크롤링 (모든 필드 포함)"""
import requests
import sqlite3
import sys
from datetime import datetime, timedelta
import time

def crawl_complete(year, start_day, end_day, worker_id):
    db_name = f'notam_complete_{year}_w{worker_id}.db'
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notam_number TEXT,
            location TEXT,
            series TEXT,
            qcode TEXT,
            qcode_mean TEXT,
            issue_time TEXT,
            effective_start TEXT,
            effective_end TEXT,
            e_text TEXT,
            full_text TEXT,
            fir TEXT,
            ais_type TEXT,
            crawl_date TEXT,
            UNIQUE(notam_number, location, effective_start, effective_end)
        )
    ''')
    conn.commit()
    
    url = "https://aim.koca.go.kr/xNotam/searchAllNotam.do"
    session = requests.Session()
    
    base_date = datetime(year, 1, 1)
    total_inserted = 0
    
    for day_num in range(start_day, end_day + 1):
        current_day = base_date + timedelta(days=day_num)
        date_str = current_day.strftime('%Y-%m-%d')
        
        for data_source in ['D', 'I']:
            payload = {
                'sch_inorout': data_source,
                'sch_airport': '',
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
                
                for item in data['DATA']:
                    try:
                        cursor.execute('''
                            INSERT INTO notams
                            (notam_number, location, series, qcode, qcode_mean,
                             issue_time, effective_start, effective_end,
                             e_text, full_text, fir, ais_type, crawl_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            item.get('NOTAM_NO', ''),
                            item.get('LOCATION', ''),
                            item.get('SERIES', ''),
                            item.get('QCODE', ''),
                            item.get('QCODE_MEAN', ''),
                            item.get('ISSUE_TIME', ''),
                            item.get('EFFECTIVESTART', ''),
                            item.get('EFFECTIVEEND', ''),
                            item.get('ECODE', ''),
                            item.get('FULL_TEXT', ''),  # 핵심!
                            item.get('FIR', ''),
                            item.get('AIS_TYPE', ''),
                            date_str
                        ))
                        total_inserted += 1
                    except sqlite3.IntegrityError:
                        pass
                
                conn.commit()
                
            except Exception as e:
                pass
            
            time.sleep(0.1)
    
    conn.close()
    print(f"[W{worker_id}] {year}: {total_inserted}")

if __name__ == '__main__':
    year = int(sys.argv[1])
    start_day = int(sys.argv[2])
    end_day = int(sys.argv[3])
    worker_id = int(sys.argv[4])
    
    crawl_complete(year, start_day, end_day, worker_id)
