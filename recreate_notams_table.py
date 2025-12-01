#!/usr/bin/env python3
"""
notams 테이블 재생성 및 데이터 크롤링
"""
import sqlite3
import sys

def recreate_table():
    conn = sqlite3.connect('notam_realtime.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("notams 테이블 재생성")
    print("=" * 80)

    # 1. 기존 notams 테이블 삭제    print("\n1. 기존 notams 테이블 삭제 중...")
    cursor.execute("DROP TABLE IF EXISTS notams")
    print("   [OK] 삭제 완료")

    # 2. notam_records에서 데이터 개수 확인
    cursor.execute("SELECT COUNT(*) FROM notam_records")
    count = cursor.fetchone()[0]
    print(f"\n2. notam_records 테이블: {count}개 레코드 존재")

    conn.commit()
    conn.close()

    print("\n3. 크롤러를 실행하여 notams 테이블 재생성 및 데이터 채우기...")
    print("   명령어: python notam_crawler_api.py")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    recreate_table()
