#!/usr/bin/env python3
"""모든 연도별 NOTAM DB를 하나로 병합"""
import sqlite3
import os

def merge_databases():
    """notam_2020.db ~ notam_2025.db를 notam_realtime.db로 병합"""

    # 최종 DB 파일
    final_db = 'notam_realtime.db'

    # 기존 파일이 있으면 삭제
    if os.path.exists(final_db):
        os.remove(final_db)
        print(f"[INFO] 기존 {final_db} 삭제")

    # 최종 DB 생성 및 연결
    conn = sqlite3.connect(final_db)
    cursor = conn.cursor()

    # notams 테이블 생성 (notam_crawler_api.py와 동일한 스키마)
    # UNIQUE 제약 없음 - 모든 데이터 병합
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notam_number TEXT,
            a_location TEXT,
            b_start_time TEXT,
            c_end_time TEXT,
            d_schedule TEXT,
            e_text TEXT,
            f_lower_limit TEXT,
            g_upper_limit TEXT,
            collected_at TEXT,
            last_updated TEXT,
            q_code TEXT,
            series_type TEXT,
            full_text TEXT,
            status TEXT DEFAULT 'ACTIVE',
            crawl_timestamp TEXT
        )
    ''')
    conn.commit()

    print(f"\n[START] 모든 연도 DB를 {final_db}로 병합 시작\n")

    # 병합할 연도별 DB 파일
    year_dbs = [
        'notam_2020.db',
        'notam_2021.db',
        'notam_2022.db',
        'notam_2023.db',
        'notam_2024.db',
        'notam_2025.db'
    ]

    total_merged = 0

    for year_db in year_dbs:
        if not os.path.exists(year_db):
            print(f"[WARN] {year_db} 파일이 없습니다. 건너뜀.")
            continue

        # 연도 DB 연결
        year_conn = sqlite3.connect(year_db)
        year_cursor = year_conn.cursor()

        # 레코드 수 확인
        year_cursor.execute("SELECT COUNT(*) FROM notams")
        count = year_cursor.fetchone()[0]

        print(f"[INFO] {year_db}: {count:,}개 레코드 병합 중...")

        # 모든 레코드 가져오기
        year_cursor.execute('''
            SELECT notam_number, a_location, b_start_time, c_end_time,
                   d_schedule, e_text, f_lower_limit, g_upper_limit,
                   collected_at, last_updated, q_code, series_type,
                   full_text, status, crawl_timestamp
            FROM notams
        ''')

        records = year_cursor.fetchall()
        year_conn.close()

        # 최종 DB에 INSERT (중복 제거)
        inserted = 0
        for record in records:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO notams
                    (notam_number, a_location, b_start_time, c_end_time,
                     d_schedule, e_text, f_lower_limit, g_upper_limit,
                     collected_at, last_updated, q_code, series_type,
                     full_text, status, crawl_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', record)
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"[ERROR] 레코드 삽입 실패: {e}")
                continue

        conn.commit()
        total_merged += inserted
        print(f"[OK] {year_db}: {inserted:,}개 병합 완료 (중복 {count - inserted}개 제거)\n")

    # 최종 통계
    cursor.execute("SELECT COUNT(*) FROM notams")
    final_count = cursor.fetchone()[0]

    conn.close()

    print("=" * 80)
    print(f"[완료] 총 {total_merged:,}개 레코드 병합 완료")
    print(f"[완료] 최종 DB: {final_db} ({final_count:,}개 레코드)")
    print("=" * 80)

    return final_db, final_count

if __name__ == '__main__':
    merge_databases()
