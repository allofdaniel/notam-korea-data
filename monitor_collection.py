#!/usr/bin/env python3
"""
NOTAM 수집 진행 상황 모니터링 스크립트
"""
import sqlite3
import time
import os

def check_progress():
    """수집 진행 상황 확인"""

    db_path = 'notam_historical.db'

    if not os.path.exists(db_path):
        print(f"❌ {db_path} 파일을 찾을 수 없습니다.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 전체 통계
    cursor.execute('SELECT COUNT(*) FROM notam_records')
    total_records = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT notam_no) FROM notam_records')
    unique_records = cursor.fetchone()[0]

    # 국내/국제 분류
    cursor.execute("SELECT COUNT(*) FROM notam_records WHERE data_source = 'domestic'")
    domestic_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM notam_records WHERE data_source = 'international'")
    intl_count = cursor.fetchone()[0]

    # 공항별 통계
    cursor.execute("""
        SELECT location, COUNT(*) as cnt
        FROM notam_records
        WHERE location != ''
        GROUP BY location
        ORDER BY cnt DESC
        LIMIT 10
    """)
    top_airports = cursor.fetchall()

    # 최근 추가된 NOTAM
    cursor.execute("""
        SELECT notam_no, location, substr(full_text, 1, 60), crawl_timestamp
        FROM notam_records
        ORDER BY id DESC
        LIMIT 5
    """)
    recent_notams = cursor.fetchall()

    conn.close()

    # 출력
    print("\n" + "="*80)
    print("📊 NOTAM 수집 진행 상황")
    print("="*80)
    print(f"\n전체 NOTAM: {total_records:,}개")
    print(f"  - Unique: {unique_records:,}개")
    print(f"  - 중복: {total_records - unique_records:,}개")
    print(f"\n분류별:")
    print(f"  - 국내 (Domestic): {domestic_count:,}개")
    print(f"  - 국제 (International): {intl_count:,}개")

    if top_airports:
        print(f"\n🛫 상위 공항 (NOTAM 개수):")
        for idx, (airport, count) in enumerate(top_airports, 1):
            print(f"  {idx:2d}. {airport:8s}: {count:,}개")

    if recent_notams:
        print(f"\n📋 최근 추가된 NOTAM (최신 5개):")
        for idx, (notam_no, location, text, timestamp) in enumerate(recent_notams, 1):
            print(f"  {idx}. {notam_no:12s} ({location:8s}): {text}...")
            if timestamp:
                print(f"     수집 시간: {timestamp}")

    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    check_progress()
