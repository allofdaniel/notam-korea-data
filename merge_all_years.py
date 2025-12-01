#!/usr/bin/env python3
"""모든 연도 병합 + JSON 생성"""
import sqlite3
import json
import os

final_db = 'notam_all_years.db'
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
        UNIQUE(notam_number, a_location, b_start_time, c_end_time)
    )
''')
conn.commit()

print("=" * 80)
print("Merging all years: 2022, 2023, 2024, 2025")
print("=" * 80)

grand_total = 0

for year in [2022, 2023, 2024, 2025]:
    year_total = 0
    year_dup = 0
    
    for worker_id in range(10):
        worker_db = f'notam_{year}_worker_{worker_id}.db'
        
        if not os.path.exists(worker_db):
            continue
        
        worker_conn = sqlite3.connect(worker_db)
        worker_cursor = worker_conn.cursor()
        
        worker_cursor.execute('''
            SELECT notam_number, a_location, b_start_time, c_end_time,
                   e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date
            FROM notams
        ''')
        
        for row in worker_cursor.fetchall():
            try:
                cursor.execute('''
                    INSERT INTO notams
                    (notam_number, a_location, b_start_time, c_end_time,
                     e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date, year)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', row + (year,))
                year_total += 1
            except sqlite3.IntegrityError:
                year_dup += 1
        
        worker_conn.close()
    
    conn.commit()
    grand_total += year_total
    print(f"{year}: {year_total:,} inserted, {year_dup:,} duplicates")

cursor.execute('SELECT COUNT(*) FROM notams')
final_count = cursor.fetchone()[0]

print(f"\nFinal total: {final_count:,} records")

# JSON 생성
print("\nGenerating JSON...")
cursor.execute('SELECT * FROM notams ORDER BY year, crawl_date')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT * FROM notams ORDER BY year, crawl_date')

data = []
for row in cursor.fetchall():
    data.append(dict(row))

json_file = 'notam_all_years.json'
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

file_size = os.path.getsize(json_file) / (1024 * 1024)

conn.close()

print("=" * 80)
print("COMPLETE!")
print("=" * 80)
print(f"Database: {final_db}")
print(f"JSON: {json_file} ({file_size:.2f} MB)")
print(f"Total records: {final_count:,}")
print("=" * 80)
