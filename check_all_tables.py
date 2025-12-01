#!/usr/bin/env python3
"""
모든 테이블 구조 확인
"""
import sqlite3

conn = sqlite3.connect('notam_realtime.db')
cursor = conn.cursor()

# 모든 테이블 목록 가져오기
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=" * 80)
print("데이터베이스 테이블 목록")
print("=" * 80)
for table in tables:
    table_name = table[0]
    print(f"\n[Table] {table_name}")

    # 테이블 스키마 확인
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    print("컬럼:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]}){' PRIMARY KEY' if col[5] else ''}")

    # 레코드 수 확인
    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
    count = cursor.fetchone()[0]
    print(f"레코드 수: {count}개")

    # 샘플 데이터 (첫 1개)
    if count > 0:
        cursor.execute(f'SELECT * FROM {table_name} LIMIT 1')
        sample = cursor.fetchone()
        column_names = [description[0] for description in cursor.description]
        print("\n샘플 데이터:")
        for name, value in zip(column_names, sample):
            value_str = str(value)[:100] + "..." if value and len(str(value)) > 100 else str(value)
            print(f"  {name}: {value_str}")

conn.close()
