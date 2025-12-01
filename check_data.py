#!/usr/bin/env python3
"""데이터 확인 스크립트"""
import sqlite3
import json
import os

db_file = 'notam_all_years.db'
json_file = 'notam_all_years.json'

print("=" * 80)
print("NOTAM Data Verification")
print("=" * 80)

# DB 확인
if os.path.exists(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM notams')
    total = cursor.fetchone()[0]
    
    print(f"\nDatabase: {db_file}")
    print(f"Total records: {total:,}")
    
    # 연도별 통계
    cursor.execute('SELECT year, COUNT(*) as cnt FROM notams GROUP BY year ORDER BY year')
    print("\nBy Year:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,} records")
    
    # 고유 NOTAM 번호
    cursor.execute('SELECT COUNT(DISTINCT notam_number) FROM notams')
    unique = cursor.fetchone()[0]
    print(f"\nUnique NOTAM numbers: {unique:,}")
    
    # 시리즈별 통계
    cursor.execute('SELECT series_type, COUNT(*) as cnt FROM notams GROUP BY series_type ORDER BY cnt DESC LIMIT 10')
    print("\nTop Series Types:")
    for row in cursor.fetchall():
        series = row[0] if row[0] else 'N/A'
        print(f"  {series}: {row[1]:,} records")
    
    # 공항별 통계
    cursor.execute('SELECT a_location, COUNT(*) as cnt FROM notams GROUP BY a_location ORDER BY cnt DESC LIMIT 10')
    print("\nTop 10 Airports:")
    for row in cursor.fetchall():
        airport = row[0] if row[0] else 'N/A'
        print(f"  {airport}: {row[1]:,} records")
    
    # 샘플 데이터 (최신 5개)
    cursor.execute('SELECT notam_number, a_location, b_start_time, series_type FROM notams ORDER BY b_start_time DESC LIMIT 5')
    print("\nSample (Latest 5 NOTAMs):")
    for row in cursor.fetchall():
        print(f"  {row[0]} | {row[1]} | {row[2]} | Type:{row[3]}")
    
    conn.close()
else:
    print(f"\nERROR: {db_file} not found!")

# JSON 확인
if os.path.exists(json_file):
    file_size = os.path.getsize(json_file) / (1024 * 1024)
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\nJSON: {json_file}")
    print(f"File size: {file_size:.2f} MB")
    print(f"Records: {len(data):,}")
    
    if len(data) > 0:
        print(f"\nSample record:")
        sample = data[0]
        for key in ['notam_number', 'a_location', 'b_start_time', 'series_type', 'year']:
            if key in sample:
                print(f"  {key}: {sample[key]}")
else:
    print(f"\nERROR: {json_file} not found!")

print("\n" + "=" * 80)
print("Files Location:")
print(f"  {os.path.abspath(os.getcwd())}")
print("=" * 80)
