#!/usr/bin/env python3
"""국내 + 국제 전체 병합"""
import sqlite3
import json
import os

final_db = 'notam_complete.db'
if os.path.exists(final_db):
    os.remove(final_db)

conn = sqlite3.connect(final_db)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE notams (
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
        year INTEGER,
        source TEXT,
        UNIQUE(notam_number, a_location, b_start_time, c_end_time)
    )
''')
conn.commit()

print("=" * 80)
print("FINAL MERGE: Domestic + International")
print("=" * 80)

total_domestic = 0
total_international = 0
total_dup = 0

# 국내 데이터
print("\n[DOMESTIC]")
for year in [2022, 2023, 2024, 2025]:
    year_total = 0
    for worker_id in range(10):
        db = f'notam_{year}_worker_{worker_id}.db'
        if not os.path.exists(db):
            continue
        
        worker_conn = sqlite3.connect(db)
        worker_cursor = worker_conn.cursor()
        worker_cursor.execute('SELECT notam_number, a_location, b_start_time, c_end_time, e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date FROM notams')
        
        for row in worker_cursor.fetchall():
            try:
                cursor.execute('INSERT INTO notams (notam_number, a_location, b_start_time, c_end_time, e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date, year, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', row + (year, 'D'))
                year_total += 1
            except sqlite3.IntegrityError:
                total_dup += 1
        
        worker_conn.close()
    
    conn.commit()
    total_domestic += year_total
    print(f"  {year}: {year_total:,}")

# 국제 데이터
print("\n[INTERNATIONAL]")
for year in [2022, 2023, 2024, 2025]:
    year_total = 0
    year_new = 0
    year_dup = 0
    
    for worker_id in range(10):
        db = f'notam_{year}_intl_{worker_id}.db'
        if not os.path.exists(db):
            continue
        
        worker_conn = sqlite3.connect(db)
        worker_cursor = worker_conn.cursor()
        worker_cursor.execute('SELECT notam_number, a_location, b_start_time, c_end_time, e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date FROM notams')
        
        for row in worker_cursor.fetchall():
            year_total += 1
            try:
                cursor.execute('INSERT INTO notams (notam_number, a_location, b_start_time, c_end_time, e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date, year, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', row + (year, 'I'))
                year_new += 1
            except sqlite3.IntegrityError:
                year_dup += 1
        
        worker_conn.close()
    
    conn.commit()
    total_international += year_total
    total_dup += year_dup
    print(f"  {year}: {year_total:,} total, {year_new:,} new, {year_dup:,} duplicates")

cursor.execute('SELECT COUNT(*) FROM notams')
final_count = cursor.fetchone()[0]

print("\n" + "=" * 80)
print("COMPLETE!")
print("=" * 80)
print(f"Domestic: {total_domestic:,}")
print(f"International: {total_international:,}")
print(f"Duplicates removed: {total_dup:,}")
print(f"\nFinal unique records: {final_count:,}")

# JSON 생성
print("\nGenerating JSON...")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT * FROM notams ORDER BY year, crawl_date')

data = [dict(row) for row in cursor.fetchall()]

json_file = 'notam_complete.json'
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

file_size = os.path.getsize(json_file) / (1024 * 1024)

print(f"JSON: {json_file} ({file_size:.2f} MB)")
print("=" * 80)

conn.close()
