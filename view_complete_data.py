#!/usr/bin/env python3
"""Complete NOTAM 데이터 뷰어 (FULL_TEXT 포함)"""
import sqlite3
import json
import os

print("=" * 80)
print("NOTAM COMPLETE DATA VIEWER (with FULL_TEXT)")
print("=" * 80)

db_file = 'notam_final_complete.db'
json_file = 'notam_final_complete.json'

# 파일 위치
print(f"\n[파일 위치]")
print(f"디렉토리: {os.path.abspath(os.getcwd())}")

# DB 파일
if os.path.exists(db_file):
    db_size = os.path.getsize(db_file) / (1024 * 1024)
    print(f"\nDatabase: {db_file} ({db_size:.2f} MB)")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 전체 통계
    cursor.execute('SELECT COUNT(*) FROM notams')
    total = cursor.fetchone()[0]
    print(f"Total records: {total:,}")

    # 연도별
    cursor.execute('SELECT year, COUNT(*) FROM notams GROUP BY year ORDER BY year')
    print("\n연도별:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}개")

    # 시리즈별 Top 10
    cursor.execute('SELECT series, COUNT(*) as cnt FROM notams GROUP BY series ORDER BY cnt DESC LIMIT 10')
    print("\n시리즈 Top 10:")
    for row in cursor.fetchall():
        series = row[0] if row[0] else 'N/A'
        print(f"  {series}: {row[1]:,}개")

    # FULL_TEXT 샘플
    cursor.execute('''
        SELECT notam_number, location, series, full_text
        FROM notams
        WHERE full_text IS NOT NULL AND full_text != ''
        ORDER BY id DESC
        LIMIT 3
    ''')
    print("\n" + "=" * 80)
    print("FULL_TEXT 샘플 (최신 3개):")
    print("=" * 80)
    for i, (notam_no, loc, series, full_text) in enumerate(cursor.fetchall(), 1):
        preview = full_text[:150] + '...' if full_text and len(full_text) > 150 else full_text
        print(f"\n[{i}] {notam_no} | {loc} | {series}")
        print(f"    {preview}")

    # FULL_TEXT 통계
    cursor.execute('SELECT COUNT(*) FROM notams WHERE full_text IS NOT NULL AND full_text != \'\'')
    with_full_text = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM notams WHERE full_text IS NULL OR full_text = \'\'')
    without_full_text = cursor.fetchone()[0]

    print("\n" + "=" * 80)
    print("FULL_TEXT 통계:")
    print(f"  있음: {with_full_text:,}개 ({with_full_text/total*100:.1f}%)")
    print(f"  없음: {without_full_text:,}개 ({without_full_text/total*100:.1f}%)")
    print("=" * 80)

    conn.close()
else:
    print(f"\nERROR: {db_file} not found!")

# JSON 파일
if os.path.exists(json_file):
    json_size = os.path.getsize(json_file) / (1024 * 1024)
    print(f"\nJSON: {json_file} ({json_size:.2f} MB)")

    # JSON 샘플
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Records: {len(data):,}")

    if data:
        print("\n샘플 레코드 (첫 번째):")
        sample = data[0]
        for key in ['notam_number', 'location', 'series', 'qcode', 'qcode_mean',
                    'issue_time', 'effective_start', 'effective_end', 'e_text', 'full_text',
                    'fir', 'ais_type', 'year', 'crawl_date']:
            if key in sample:
                value = sample[key]
                if key in ['e_text', 'full_text'] and value and len(str(value)) > 80:
                    value = str(value)[:80] + '...'
                print(f"  {key}: {value}")
else:
    print(f"\nERROR: {json_file} not found!")

print("\n" + "=" * 80)
print("데이터 탐색 방법:")
print("  1. SQLite Browser 사용: https://sqlitebrowser.org/")
print("  2. Python으로 직접 조회:")
print("     import sqlite3")
print("     conn = sqlite3.connect('notam_final_complete.db')")
print("     cursor = conn.cursor()")
print("     cursor.execute('SELECT * FROM notams LIMIT 10')")
print("  3. JSON 파일 직접 열기:")
print("     import json")
print("     data = json.load(open('notam_final_complete.json'))")
print("\n다음 단계:")
print("  py upload_complete_to_s3.py  # S3에 업로드")
print("=" * 80)
