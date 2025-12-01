#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
크롤링 결과 확인 스크립트
"""
import sqlite3
from datetime import datetime

def check_results():
    conn = sqlite3.connect('notam_realtime.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n" + "="*80)
    print("NOTAM 크롤링 결과 확인")
    print("="*80 + "\n")

    # 1. 전체 레코드 수
    cursor.execute('SELECT COUNT(*) as count FROM notam_records')
    total_records = cursor.fetchone()['count']
    print(f"1. 총 NOTAM 레코드: {total_records}개\n")

    # 2. 데이터 소스별 레코드 수
    cursor.execute('''
        SELECT data_source, COUNT(*) as count
        FROM notam_records
        GROUP BY data_source
    ''')
    print("2. 데이터 소스별 레코드:")
    for row in cursor.fetchall():
        print(f"   - {row['data_source']}: {row['count']}개")

    # 3. 최근 크롤링 로그
    print("\n3. 최근 크롤링 로그 (최근 5개):")
    print("-"*80)
    cursor.execute('''
        SELECT crawl_timestamp, data_source, status,
               records_found, records_saved, execution_time
        FROM crawl_logs
        ORDER BY crawl_timestamp DESC
        LIMIT 5
    ''')

    for row in cursor.fetchall():
        print(f"시간: {row['crawl_timestamp']}")
        print(f"소스: {row['data_source']}")
        print(f"상태: {row['status']}")
        print(f"발견: {row['records_found']}개 | 저장: {row['records_saved']}개")
        print(f"실행시간: {row['execution_time']:.2f}초")
        print("-"*80)

    # 4. 최근 NOTAM 레코드 샘플
    print("\n4. 최근 NOTAM 레코드 샘플 (최근 3개):")
    print("-"*80)
    cursor.execute('''
        SELECT notam_no, location, notam_type, issue_time,
               start_time, end_time, qcode, full_text
        FROM notam_records
        ORDER BY crawl_timestamp DESC
        LIMIT 3
    ''')

    for row in cursor.fetchall():
        print(f"NOTAM 번호: {row['notam_no']}")
        print(f"공항: {row['location']}")
        print(f"타입: {row['notam_type']}")
        print(f"발행시간: {row['issue_time']}")
        print(f"유효기간: {row['start_time']} ~ {row['end_time']}")
        print(f"Q코드: {row['qcode']}")
        print(f"내용: {row['full_text'][:100]}...")
        print("-"*80)

    # 5. 크롤링 성공률
    cursor.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success
        FROM crawl_logs
    ''')
    row = cursor.fetchone()
    if row['total'] > 0:
        success_rate = (row['success'] / row['total']) * 100
        print(f"\n5. 크롤링 성공률: {success_rate:.1f}% ({row['success']}/{row['total']})")

    conn.close()
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    check_results()