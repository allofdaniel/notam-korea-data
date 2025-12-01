#!/usr/bin/env python3
"""워커 DB들을 병합하고 중복 확인"""
import sqlite3
import os

# 최종 DB
final_db = 'notam_2024_final.db'
if os.path.exists(final_db):
    os.remove(final_db)

conn = sqlite3.connect(final_db)
cursor = conn.cursor()

# 테이블 생성 (UNIQUE 제약으로 중복 자동 제거)
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
        UNIQUE(notam_number, a_location, b_start_time, c_end_time)
    )
''')
conn.commit()

print("=" * 80)
print("Merging worker databases")
print("=" * 80)

total_read = 0
total_inserted = 0
total_duplicates = 0

for worker_id in range(10):
    worker_db = f'notam_2024_worker_{worker_id}.db'
    
    if not os.path.exists(worker_db):
        continue
    
    worker_conn = sqlite3.connect(worker_db)
    worker_cursor = worker_conn.cursor()
    
    worker_cursor.execute('SELECT COUNT(*) FROM notams')
    count = worker_cursor.fetchone()[0]
    total_read += count
    
    worker_cursor.execute('''
        SELECT notam_number, a_location, b_start_time, c_end_time,
               e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date
        FROM notams
    ''')
    
    inserted = 0
    duplicates = 0
    
    for row in worker_cursor.fetchall():
        try:
            cursor.execute('''
                INSERT INTO notams
                (notam_number, a_location, b_start_time, c_end_time,
                 e_text, f_lower_limit, g_upper_limit, q_code, series_type, crawl_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', row)
            inserted += 1
        except sqlite3.IntegrityError:
            duplicates += 1
    
    conn.commit()
    worker_conn.close()
    
    total_inserted += inserted
    total_duplicates += duplicates
    
    print(f"Worker {worker_id}: {count:,} read, {inserted:,} inserted, {duplicates:,} duplicates")

# 최종 통계
cursor.execute('SELECT COUNT(*) FROM notams')
final_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(DISTINCT notam_number) FROM notams')
unique_notam_numbers = cursor.fetchone()[0]

conn.close()

print("\n" + "=" * 80)
print("MERGE COMPLETE")
print("=" * 80)
print(f"Total read: {total_read:,}")
print(f"Total inserted: {total_inserted:,}")
print(f"Total duplicates: {total_duplicates:,}")
print(f"\nFinal DB: {final_db}")
print(f"Final records: {final_count:,}")
print(f"Unique NOTAM numbers: {unique_notam_numbers:,}")
print("=" * 80)
