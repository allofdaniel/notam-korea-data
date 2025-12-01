#!/usr/bin/env python3
"""국제 NOTAM 크롤링"""
import requests
import sqlite3
import sys
from datetime import datetime, timedelta
import time

def crawl_international(year, start_day, end_day, worker_id):
    db_name = f'notam_{year}_intl_{worker_id}.db'
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notam_number TEXT,
            a_location TEXT,
            b_start_time TEXT,
            c_end_time TEXT,
            e_text TEXT,
            f_lower_limit TEXT,
            g_upper_limit TEXT,
            q_code TEXT,
            series_type TEXT,
            crawl_date TEXT,
            UNIQUE(notam_number, a_location, b_start_time, c_end_time)
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
        
        payload = {
            'sch_inorout': 'I',  # International
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
            
            for item in data['DATA']:
                try:
                    cursor.execute('''
                        INSERT INTO notams
                        (notam_number, a_location, b_start_time, c_end_time,
                         e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('NOTAM_NO', ''),
                        item.get('LOCATION', ''),
                        item.get('START_TIME', ''),
                        item.get('END_TIME', ''),
                        item.get('E', ''),
                        item.get('F', ''),
                        item.get('G', ''),
                        item.get('Q_CODE', ''),
                        item.get('SERIES', ''),
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
    print(f"[Intl Worker {worker_id}] {year}: {total_inserted} records")

if __name__ == '__main__':
    year = int(sys.argv[1])
    start_day = int(sys.argv[2])
    end_day = int(sys.argv[3])
    worker_id = int(sys.argv[4])
    
    crawl_international(year, start_day, end_day, worker_id)
