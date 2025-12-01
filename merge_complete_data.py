#!/usr/bin/env python3
"""병합: notam_complete_*_w*.db → notam_final_complete.db"""
import sqlite3
import glob
import json
import os

print("=" * 80)
print("NOTAM Complete Data Merge (with FULL_TEXT)")
print("=" * 80)

# 최종 DB 생성
final_db = 'notam_final_complete.db'
if os.path.exists(final_db):
    os.remove(final_db)
    print(f"\n기존 {final_db} 삭제")

conn_final = sqlite3.connect(final_db)
cursor_final = conn_final.cursor()

# 테이블 생성 (FULL_TEXT 포함)
cursor_final.execute('''
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
        year INTEGER,
        UNIQUE(notam_number, location, effective_start, effective_end)
    )
''')
conn_final.commit()

# Worker DB 찾기
worker_dbs = sorted(glob.glob('notam_complete_*_w*.db'))

print(f"\n발견된 Worker DB: {len(worker_dbs)}개")

total_inserted = 0
total_duplicates = 0
year_stats = {}

for db_file in worker_dbs:
    print(f"\n처리 중: {db_file}")

    # 연도 추출
    year = int(db_file.split('_')[2])

    conn_src = sqlite3.connect(db_file)
    cursor_src = conn_src.cursor()

    # 레코드 수 확인
    cursor_src.execute('SELECT COUNT(*) FROM notams')
    count = cursor_src.fetchone()[0]
    print(f"  레코드: {count:,}개")

    # 모든 레코드 가져오기
    cursor_src.execute('''
        SELECT notam_number, location, series, qcode, qcode_mean,
               issue_time, effective_start, effective_end,
               e_text, full_text, fir, ais_type, crawl_date
        FROM notams
    ''')

    inserted = 0
    duplicates = 0

    for row in cursor_src.fetchall():
        try:
            cursor_final.execute('''
                INSERT INTO notams
                (notam_number, location, series, qcode, qcode_mean,
                 issue_time, effective_start, effective_end,
                 e_text, full_text, fir, ais_type, crawl_date, year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', row + (year,))
            inserted += 1
            total_inserted += 1
        except sqlite3.IntegrityError:
            duplicates += 1
            total_duplicates += 1

    conn_src.close()
    conn_final.commit()

    print(f"  삽입: {inserted:,}개, 중복: {duplicates:,}개")

    if year not in year_stats:
        year_stats[year] = 0
    year_stats[year] += inserted

# 최종 통계
print("\n" + "=" * 80)
print("병합 완료!")
print("=" * 80)
print(f"\n총 레코드: {total_inserted:,}개")
print(f"총 중복: {total_duplicates:,}개")

print("\n연도별 통계:")
for year in sorted(year_stats.keys()):
    print(f"  {year}: {year_stats[year]:,}개")

# FULL_TEXT 샘플 확인
cursor_final.execute('''
    SELECT notam_number, location, full_text
    FROM notams
    WHERE full_text IS NOT NULL AND full_text != ''
    LIMIT 3
''')

print("\n" + "=" * 80)
print("FULL_TEXT 샘플 (첫 3개):")
print("=" * 80)

for i, (notam_no, loc, full_text) in enumerate(cursor_final.fetchall(), 1):
    preview = full_text[:200] + '...' if full_text and len(full_text) > 200 else full_text
    print(f"\n[{i}] {notam_no} ({loc})")
    print(f"FULL_TEXT: {preview}")

# FULL_TEXT 없는 레코드 확인
cursor_final.execute('''
    SELECT COUNT(*)
    FROM notams
    WHERE full_text IS NULL OR full_text = ''
''')
empty_full_text = cursor_final.fetchone()[0]

print("\n" + "=" * 80)
print(f"FULL_TEXT 없는 레코드: {empty_full_text:,}개")
print("=" * 80)

conn_final.close()

# 파일 크기
db_size = os.path.getsize(final_db) / (1024 * 1024)
print(f"\n파일: {final_db} ({db_size:.2f} MB)")

# JSON 생성
print("\n" + "=" * 80)
print("JSON 파일 생성 중...")
print("=" * 80)

conn = sqlite3.connect(final_db)
cursor = conn.cursor()

cursor.execute('SELECT * FROM notams')
columns = [desc[0] for desc in cursor.description]
data = []

for row in cursor.fetchall():
    record = dict(zip(columns, row))
    data.append(record)

json_file = 'notam_final_complete.json'
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

conn.close()

json_size = os.path.getsize(json_file) / (1024 * 1024)
print(f"\n파일: {json_file} ({json_size:.2f} MB)")
print(f"레코드: {len(data):,}개")

print("\n" + "=" * 80)
print("완료!")
print("=" * 80)
print("\n생성된 파일:")
print(f"  1. {final_db} ({db_size:.2f} MB)")
print(f"  2. {json_file} ({json_size:.2f} MB)")
print("\n다음 단계:")
print("  1. py view_complete_data.py  # 데이터 확인")
print("  2. py upload_complete_to_s3.py  # S3 업로드")
print("=" * 80)
