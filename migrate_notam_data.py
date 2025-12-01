#!/usr/bin/env python3
"""
notam_records 테이블 데이터를 notams 테이블로 마이그레이션
API 서버가 읽을 수 있도록 스키마 통합
"""
import sqlite3
from datetime import datetime

def migrate_data():
    """데이터 마이그레이션 실행"""

    # 모든 DB 파일 처리
    db_files = ['notam_realtime.db', 'notam_historical.db']

    for db_file in db_files:
        try:
            print(f"\n{'='*80}")
            print(f"📦 처리 중: {db_file}")
            print(f"{'='*80}")

            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # notam_records 테이블 확인
            cursor.execute("SELECT COUNT(*) FROM notam_records")
            total_records = cursor.fetchone()[0]
            print(f"📊 notam_records 테이블: {total_records}개")

            # notams 테이블에 없는 컬럼 확인 및 추가
            cursor.execute("PRAGMA table_info(notams)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            # notam_records의 데이터를 notams로 복사
            print(f"\n🔄 데이터 마이그레이션 시작...")

            # notam_records에서 데이터 읽기
            cursor.execute("""
                SELECT
                    notam_no, notam_type, location, issue_time,
                    start_time, end_time, qcode,
                    full_text, full_text_detail,
                    data_source, crawl_timestamp
                FROM notam_records
            """)

            records = cursor.fetchall()
            migrated = 0

            for record in records:
                (notam_no, notam_type, location, issue_time,
                 start_time, end_time, qcode,
                 full_text, full_text_detail,
                 data_source, crawl_timestamp) = record

                try:
                    # notams 테이블에 삽입 (중복 시 업데이트)
                    cursor.execute("""
                        INSERT INTO notams (
                            notam_number, series_type, a_location,
                            b_start_time, c_end_time, q_code,
                            e_text, full_text, status, crawl_timestamp,
                            collected_at, last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(notam_number) DO UPDATE SET
                            a_location = excluded.a_location,
                            e_text = excluded.e_text,
                            q_code = excluded.q_code,
                            status = excluded.status,
                            last_updated = excluded.last_updated
                    """, (
                        notam_no,
                        notam_type or (notam_no[0] if notam_no else 'A'),
                        location,
                        start_time,
                        end_time,
                        qcode,
                        full_text[:500] if full_text else '',
                        full_text_detail or full_text,
                        'ACTIVE',
                        crawl_timestamp or datetime.now().isoformat(),
                        crawl_timestamp or datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))

                    if cursor.rowcount > 0:
                        migrated += 1

                except Exception as e:
                    print(f"  ⚠️  오류 ({notam_no}): {e}")
                    continue

            conn.commit()

            # 최종 통계
            cursor.execute("SELECT COUNT(*) FROM notams")
            total_notams = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT a_location) FROM notams WHERE a_location != ''")
            total_airports = cursor.fetchone()[0]

            print(f"\n✅ 마이그레이션 완료!")
            print(f"  - 마이그레이션: {migrated}개")
            print(f"  - 전체 NOTAM: {total_notams}개")
            print(f"  - 공항 수: {total_airports}개")

            conn.close()

        except Exception as e:
            print(f"❌ {db_file} 처리 실패: {e}")
            continue

    print(f"\n{'='*80}")
    print("🎉 전체 마이그레이션 완료!")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    migrate_data()
