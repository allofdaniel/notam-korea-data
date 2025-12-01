#!/usr/bin/env python3
"""
모든 Historical NOTAM 데이터를 메인 DB로 통합 마이그레이션
- notam_historical.db (2020-2025)
- notam_2000_2019.db (2000-2019)
→ notam_realtime.db (메인 운영 DB)
"""
import sqlite3
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def migrate_historical_to_main():
    """모든 historical DB를 메인 DB로 마이그레이션"""

    # 소스 DB 파일들
    source_dbs = [
        ('notam_historical.db', '2020-2025년 데이터'),
        ('notam_2000_2019.db', '2000-2019년 데이터')
    ]

    # 타겟 DB
    target_db = 'notam_realtime.db'

    logger.info(f"\n{'='*80}")
    logger.info("🚀 Historical NOTAM 통합 마이그레이션 시작")
    logger.info(f"{'='*80}\n")

    # 타겟 DB 연결
    target_conn = sqlite3.connect(target_db)
    target_cursor = target_conn.cursor()

    total_migrated = 0
    total_skipped = 0
    stats_by_source = {}

    for source_db, label in source_dbs:
        if not os.path.exists(source_db):
            logger.warning(f"⚠️  {source_db} 파일 없음 - 스킵")
            continue

        logger.info(f"\n📦 처리 중: {source_db} ({label})")
        logger.info(f"{'─'*80}")

        try:
            # 소스 DB 연결
            source_conn = sqlite3.connect(source_db)
            source_cursor = source_conn.cursor()

            # 소스 DB 통계
            source_cursor.execute("SELECT COUNT(*) FROM notam_records")
            total_records = source_cursor.fetchone()[0]

            source_cursor.execute("SELECT COUNT(*) FROM notam_records WHERE data_source='domestic'")
            domestic_count = source_cursor.fetchone()[0]

            source_cursor.execute("SELECT COUNT(*) FROM notam_records WHERE data_source='international'")
            intl_count = source_cursor.fetchone()[0]

            logger.info(f"  📊 소스 통계:")
            logger.info(f"     전체: {total_records:,}개")
            logger.info(f"     국내: {domestic_count:,}개")
            logger.info(f"     국제: {intl_count:,}개")

            if total_records == 0:
                logger.warning(f"  ⚠️  데이터 없음 - 스킵")
                source_conn.close()
                continue

            # 데이터 읽기
            source_cursor.execute("""
                SELECT
                    notam_no, notam_type, location, issue_time,
                    start_time, end_time, qcode,
                    full_text, full_text_detail,
                    data_source, crawl_timestamp
                FROM notam_records
            """)

            records = source_cursor.fetchall()
            migrated = 0
            skipped = 0

            logger.info(f"\n  🔄 마이그레이션 시작...")

            for record in records:
                (notam_no, notam_type, location, issue_time,
                 start_time, end_time, qcode,
                 full_text, full_text_detail,
                 data_source, crawl_timestamp) = record

                try:
                    # notams 테이블에 삽입 (중복 시 업데이트)
                    target_cursor.execute("""
                        INSERT INTO notams (
                            notam_number, series_type, a_location,
                            b_start_time, c_end_time, q_code,
                            e_text, full_text, status,
                            crawl_timestamp, collected_at, last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(notam_number) DO UPDATE SET
                            a_location = excluded.a_location,
                            e_text = excluded.e_text,
                            q_code = excluded.q_code,
                            full_text = excluded.full_text,
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
                        'HISTORICAL',
                        crawl_timestamp or datetime.now().isoformat(),
                        crawl_timestamp or datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))

                    if target_cursor.rowcount > 0:
                        migrated += 1
                        if migrated % 1000 == 0:
                            logger.info(f"     진행: {migrated:,}개 마이그레이션 완료...")
                    else:
                        skipped += 1

                except Exception as e:
                    logger.debug(f"  ⚠️  오류 ({notam_no}): {e}")
                    skipped += 1
                    continue

            # 커밋
            target_conn.commit()

            # 통계 저장
            stats_by_source[label] = {
                'total': total_records,
                'migrated': migrated,
                'skipped': skipped,
                'domestic': domestic_count,
                'international': intl_count
            }

            total_migrated += migrated
            total_skipped += skipped

            logger.info(f"\n  ✅ 완료!")
            logger.info(f"     마이그레이션: {migrated:,}개")
            logger.info(f"     스킵: {skipped:,}개")

            source_conn.close()

        except Exception as e:
            logger.error(f"  ❌ {source_db} 처리 실패: {e}")
            continue

    # 최종 통계
    target_cursor.execute("SELECT COUNT(*) FROM notams")
    final_count = target_cursor.fetchone()[0]

    target_cursor.execute("SELECT COUNT(DISTINCT a_location) FROM notams WHERE a_location != ''")
    airport_count = target_cursor.fetchone()[0]

    target_conn.close()

    # 결과 출력
    logger.info(f"\n{'='*80}")
    logger.info("✅ 통합 마이그레이션 완료!")
    logger.info(f"{'='*80}")

    logger.info(f"\n📊 마이그레이션 통계:")
    for label, stats in stats_by_source.items():
        logger.info(f"\n  [{label}]")
        logger.info(f"    - 원본: {stats['total']:,}개 (국내 {stats['domestic']:,}, 국제 {stats['international']:,})")
        logger.info(f"    - 마이그레이션: {stats['migrated']:,}개")
        logger.info(f"    - 스킵: {stats['skipped']:,}개")

    logger.info(f"\n📦 최종 메인 DB 통계:")
    logger.info(f"  - 전체 NOTAM: {final_count:,}개")
    logger.info(f"  - 총 마이그레이션: {total_migrated:,}개")
    logger.info(f"  - 총 스킵: {total_skipped:,}개")
    logger.info(f"  - 공항 수: {airport_count}개")

    logger.info(f"\n💾 데이터베이스: {target_db}")
    logger.info(f"{'='*80}\n")

    return {
        'success': True,
        'total_migrated': total_migrated,
        'total_skipped': total_skipped,
        'final_count': final_count,
        'stats_by_source': stats_by_source
    }


if __name__ == '__main__':
    try:
        result = migrate_historical_to_main()

        if result['success']:
            print(f"\n✅ 성공! 총 {result['total_migrated']:,}개 NOTAM 마이그레이션 완료")
            exit(0)
        else:
            print("\n❌ 마이그레이션 실패")
            exit(1)

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
