#!/usr/bin/env python3
"""전체 NOTAM 최종 병합"""
import sqlite3
import json
import os

final_db = 'notam_final_all.db'
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
print("FINAL MERGE: ALL NOTAMs (2022-2025)")
print("=" * 80)

grand_total = 0

for year in [2022, 2023, 2024, 2025]:
    year_total = 0
    year_dup = 0
    
    for worker_id in range(10):
        db = f'notam_all_{year}_worker_{worker_id}.db'
        if not os.path.exists(db):
            continue
        
        worker_conn = sqlite3.connect(db)
        worker_cursor = worker_conn.cursor()
        worker_cursor.execute('SELECT notam_number, a_location, b_start_time, c_end_time, e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date FROM notams')
        
        for row in worker_cursor.fetchall():
            try:
                cursor.execute('INSERT INTO notams (notam_number, a_location, b_start_time, c_end_time, e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date, year) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', row + (year,))
                year_total += 1
            except sqlite3.IntegrityError:
                year_dup += 1
        
        worker_conn.close()
    
    conn.commit()
    grand_total += year_total
    print(f"{year}: {year_total:,} unique ({year_dup:,} duplicates)")

cursor.execute('SELECT COUNT(*) FROM notams')
final_count = cursor.fetchone()[0]

print(f"\n" + "=" * 80)
print(f"Total unique records: {final_count:,}")
print("=" * 80)

# JSON 생성
print("\nGenerating JSON...")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT * FROM notams ORDER BY year, crawl_date')

data = [dict(row) for row in cursor.fetchall()]

json_file = 'notam_final_all.json'
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

file_size = os.path.getsize(json_file) / (1024 * 1024)

print(f"JSON: {json_file} ({file_size:.2f} MB)")

# 통계
cursor.execute('SELECT series_type, COUNT(*) FROM notams GROUP BY series_type ORDER BY COUNT(*) DESC')
print("\nBy Series:")
for row in cursor.fetchall():
    series = row[0] if row[0] else 'N/A'
    print(f"  {series}: {row[1]:,}")

print("=" * 80)

conn.close()
