#!/usr/bin/env python3
"""로컬 NOTAM 데이터 뷰어"""
import sqlite3
import json
import os

print("=" * 80)
print("NOTAM DATA VIEWER")
print("=" * 80)

db_file = 'notam_final_all.db'
json_file = 'notam_final_all.json'

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
    cursor.execute('SELECT series_type, COUNT(*) as cnt FROM notams GROUP BY series_type ORDER BY cnt DESC LIMIT 10')
    print("\n시리즈 Top 10:")
    for row in cursor.fetchall():
        series = row[0] if row[0] else 'N/A'
        print(f"  {series}: {row[1]:,}개")
    
    # 최신 5개
    cursor.execute('SELECT notam_number, a_location, series_type, crawl_date FROM notams ORDER BY id DESC LIMIT 5')
    print("\n최신 5개:")
    for row in cursor.fetchall():
        print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]}")
    
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
        for key in ['notam_number', 'a_location', 'series_type', 'e_text', 'year', 'crawl_date']:
            if key in sample:
                value = sample[key]
                if key == 'e_text' and value and len(value) > 50:
                    value = value[:50] + '...'
                print(f"  {key}: {value}")
else:
    print(f"\nERROR: {json_file} not found!")

print("\n" + "=" * 80)
print("데이터 탐색 방법:")
print("  1. SQLite Browser 사용: https://sqlitebrowser.org/")
print("  2. Python으로 직접 조회:")
print("     import sqlite3")
print("     conn = sqlite3.connect('notam_final_all.db')")
print("     cursor = conn.cursor()")
print("     cursor.execute('SELECT * FROM notams LIMIT 10')")
print("  3. JSON 파일 직접 열기:")
print("     import json")
print("     data = json.load(open('notam_final_all.json'))")
print("=" * 80)
