#!/usr/bin/env python3
"""
DynamoDB에서 NOTAM 데이터를 가져와 SQLite로 동기화
"""
import boto3
import sqlite3
from datetime import datetime
from decimal import Decimal
import json

# DynamoDB 연결
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
table = dynamodb.Table('NOTAM_Records')

# SQLite 연결
conn = sqlite3.connect('notam_realtime.db')
cursor = conn.cursor()

# 테이블 생성 (이미 있으면 무시)
cursor.execute('''
CREATE TABLE IF NOT EXISTS notams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notam_number TEXT UNIQUE,
    series_type TEXT,
    a_location TEXT,
    b_start_time TEXT,
    c_end_time TEXT,
    d_schedule TEXT,
    e_text TEXT,
    f_lower_limit TEXT,
    g_upper_limit TEXT,
    q_code TEXT,
    collected_at TEXT,
    last_updated TEXT,
    full_text TEXT,
    status TEXT,
    crawl_timestamp TEXT
)
''')

print("🔄 DynamoDB → SQLite 동기화 시작...\n")

# DynamoDB 스캔 (페이지네이션 지원)
total_items = 0
new_items = 0
updated_items = 0

response = table.scan()
items = response.get('Items', [])

while True:
    for item in items:
        total_items += 1

        # Decimal을 float/int로 변환
        def convert_decimal(obj):
            if isinstance(obj, Decimal):
                return int(obj) if obj % 1 == 0 else float(obj)
            return obj

        # 데이터 매핑
        notam_number = item.get('notam_id', item.get('id', f"DDB_{total_items}"))
        location = item.get('location', item.get('a_location', ''))
        qcode = item.get('qcode', item.get('q_code', ''))
        full_text = item.get('full_text', item.get('e_text', ''))
        status = item.get('status', 'ACTIVE')
        crawl_timestamp = item.get('crawl_timestamp', datetime.now().isoformat())

        # NOTAM 번호에서 시리즈 타입 추출 (예: A0001/25 -> A)
        series_type = notam_number[0] if notam_number and notam_number[0].isalpha() else 'A'

        # 시간 정보 파싱 (있으면)
        start_time = item.get('start_time', item.get('b_start_time', ''))
        end_time = item.get('end_time', item.get('c_end_time', ''))

        # E_text에서 고도 정보 추출 시도
        lower_limit = item.get('f_lower_limit', '')
        upper_limit = item.get('g_upper_limit', '')

        try:
            # UPSERT (있으면 업데이트, 없으면 삽입)
            cursor.execute('''
                INSERT INTO notams (
                    notam_number, series_type, a_location,
                    b_start_time, c_end_time, d_schedule,
                    e_text, f_lower_limit, g_upper_limit,
                    q_code, collected_at, last_updated,
                    full_text, status, crawl_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(notam_number) DO UPDATE SET
                    a_location = excluded.a_location,
                    e_text = excluded.e_text,
                    q_code = excluded.q_code,
                    status = excluded.status,
                    last_updated = excluded.last_updated,
                    crawl_timestamp = excluded.crawl_timestamp
            ''', (
                notam_number, series_type, location,
                start_time, end_time, '',
                full_text[:500] if full_text else '',  # E_text (요약)
                lower_limit, upper_limit,
                qcode, crawl_timestamp, datetime.now().isoformat(),
                full_text, status, crawl_timestamp
            ))

            if cursor.rowcount > 0:
                if cursor.lastrowid:
                    new_items += 1
                else:
                    updated_items += 1

        except Exception as e:
            print(f"⚠️  에러 ({notam_number}): {e}")

        # 진행상황 표시 (100개마다)
        if total_items % 100 == 0:
            print(f"  처리 중... {total_items}개 (신규: {new_items}, 업데이트: {updated_items})")

    # 다음 페이지가 있으면 계속
    if 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items = response.get('Items', [])
    else:
        break

conn.commit()

print(f"\n✅ 동기화 완료!")
print(f"  - 총 처리: {total_items}개")
print(f"  - 신규 추가: {new_items}개")
print(f"  - 업데이트: {updated_items}개")

# 최종 통계
cursor.execute("SELECT COUNT(*) FROM notams")
total_db = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT a_location) FROM notams WHERE a_location != ''")
total_airports = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM notams WHERE status = 'ACTIVE'")
active_notams = cursor.fetchone()[0]

print(f"\n📊 SQLite DB 현황:")
print(f"  - 전체 NOTAM: {total_db}개")
print(f"  - 공항 수: {total_airports}개")
print(f"  - 활성 NOTAM: {active_notams}개")

# 최근 5개 샘플
print(f"\n📄 최근 5개 NOTAM:")
cursor.execute("""
    SELECT notam_number, a_location, substr(e_text, 1, 60)
    FROM notams
    ORDER BY crawl_timestamp DESC
    LIMIT 5
""")
for i, (num, loc, text) in enumerate(cursor.fetchall(), 1):
    print(f"  {i}. {num} ({loc}): {text}...")

conn.close()
print("\n🎉 완료!")
