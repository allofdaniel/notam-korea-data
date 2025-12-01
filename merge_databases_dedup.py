#!/usr/bin/env python3
"""모든 연도별 NOTAM DB를 중복 제거하여 병합"""
import sqlite3
import os
from collections import defaultdict

def merge_databases_with_dedup():
    """notam_2022.db ~ notam_2025.db를 중복 제거하여 병합"""

    # 최종 DB 파일
    final_db = 'notam_realtime.db'

    # 기존 파일이 있으면 삭제
    if os.path.exists(final_db):
        os.remove(final_db)
        print(f"[INFO] Removed existing {final_db}")

    # 최종 DB 생성 및 연결
    conn = sqlite3.connect(final_db)
    cursor = conn.cursor()

    # notams 테이블 생성
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
            crawl_timestamp TEXT,
            UNIQUE(notam_number, a_location, b_start_time, c_end_time)
        )
    ''')
    conn.commit()

    print("=" * 80)
    print("Merging databases with deduplication")
    print("=" * 80 + "\n")

    # 병합할 연도별 DB 파일 (2022-2025만)
    year_dbs = [
        'notam_2022.db',
        'notam_2023.db',
        'notam_2024.db',
        'notam_2025.db'
    ]

    total_read = 0
    total_inserted = 0
    total_duplicates = 0

    for year_db in year_dbs:
        if not os.path.exists(year_db):
            print(f"[WARN] {year_db} not found. Skipping.")
            continue

        # 연도 DB 연결
        year_conn = sqlite3.connect(year_db)
        year_cursor = year_conn.cursor()

        # 레코드 수 확인
        year_cursor.execute("SELECT COUNT(*) FROM notams")
        count = year_cursor.fetchone()[0]
        total_read += count

        print(f"[INFO] Processing {year_db}: {count:,} records")

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

        # 최종 DB에 INSERT (UNIQUE 제약으로 자동 중복 제거)
        inserted = 0
        duplicates = 0

        for record in records:
            try:
                cursor.execute('''
                    INSERT INTO notams
                    (notam_number, a_location, b_start_time, c_end_time,
                     d_schedule, e_text, f_lower_limit, g_upper_limit,
                     collected_at, last_updated, q_code, series_type,
                     full_text, status, crawl_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', record)
                inserted += 1
            except sqlite3.IntegrityError:
                # UNIQUE 제약 위반 = 중복
                duplicates += 1
            except Exception as e:
                print(f"[ERROR] Insert failed: {e}")
                duplicates += 1

        conn.commit()
        total_inserted += inserted
        total_duplicates += duplicates

        print(f"  Inserted: {inserted:,}")
        print(f"  Duplicates removed: {duplicates:,}\n")

    # 최종 통계
    cursor.execute("SELECT COUNT(*) FROM notams")
    final_count = cursor.fetchone()[0]

    # 고유 NOTAM 번호 수
    cursor.execute("SELECT COUNT(DISTINCT notam_number) FROM notams")
    unique_notam_numbers = cursor.fetchone()[0]

    conn.close()

    print("=" * 80)
    print("Merge Complete!")
    print("=" * 80)
    print(f"Total records read: {total_read:,}")
    print(f"Total records inserted: {total_inserted:,}")
    print(f"Total duplicates removed: {total_duplicates:,}")
    print(f"Final DB: {final_db}")
    print(f"Final record count: {final_count:,}")
    print(f"Unique NOTAM numbers: {unique_notam_numbers:,}")
    print("=" * 80)

    return final_db, final_count

if __name__ == '__main__':
    merge_databases_with_dedup()
