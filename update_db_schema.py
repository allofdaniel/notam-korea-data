#!/usr/bin/env python3
"""
SQLite DB 스키마 업데이트
"""
import sqlite3

conn = sqlite3.connect('notam_realtime.db')
cursor = conn.cursor()

print("🔧 DB 스키마 업데이트 중...")

# 기존 데이터 백업
cursor.execute("SELECT COUNT(*) FROM notams")
existing_count = cursor.fetchone()[0]
print(f"  기존 NOTAM: {existing_count}개")

# 필요한 컬럼 추가
columns_to_add = [
    ('full_text', 'TEXT'),
    ('status', 'TEXT DEFAULT "ACTIVE"'),
    ('crawl_timestamp', 'TEXT')
]

for col_name, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE notams ADD COLUMN {col_name} {col_type}")
        print(f"  ✅ 컬럼 추가: {col_name}")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print(f"  ⏭️  이미 존재: {col_name}")
        else:
            print(f"  ⚠️  에러 ({col_name}): {e}")

conn.commit()
conn.close()

print("\n✅ 스키마 업데이트 완료!")
