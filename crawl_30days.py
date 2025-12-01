#!/usr/bin/env python3
"""
30일치 NOTAM 데이터 수집 스크립트
더 많은 테스트 데이터를 위해 30일(720시간)의 NOTAM을 크롤링합니다.
"""
import sys
import sqlite3
from datetime import datetime, timedelta

# notam_crawler_api 모듈 import
try:
    from notam_crawler_api import NotamCrawler
except ImportError:
    print("[ERROR] notam_crawler_api.py를 찾을 수 없습니다.")
    sys.exit(1)

def crawl_30_days():
    """30일치 NOTAM 크롤링"""
    print("=" * 80)
    print("30일치 NOTAM 크롤링 시작")
    print("=" * 80)

    # 시간 설정: 현재부터 30일 전까지
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=30)

    print(f"\n[INFO] 크롤링 기간:")
    print(f"  시작: {start_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  종료: {end_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  기간: 30일 (720시간)")

    # 크롤러 초기화
    crawler = NotamCrawler(db_path='notam_realtime.db')

    print("\n[INFO] 크롤링 시작 중...")
    print("[INFO] 이 작업은 수십 분이 걸릴 수 있습니다.")
    print("[INFO] 진행 상황을 확인하려면 로그를 지켜보세요.\n")

    # 크롤링 실행
    try:
        crawler.crawl_realtime(
            start_time=start_time,
            end_time=end_time,
            interval_hours=24  # 24시간 단위로 나누어 크롤링
        )
        print("\n[OK] 크롤링 완료!")
    except Exception as e:
        print(f"\n[ERROR] 크롤링 중 오류 발생: {e}")
        return False

    # 결과 확인
    print("\n" + "=" * 80)
    print("크롤링 결과")
    print("=" * 80)

    try:
        conn = sqlite3.connect('notam_realtime.db')
        cursor = conn.cursor()

        # 총 NOTAM 개수
        cursor.execute("SELECT COUNT(*) FROM notams")
        total_count = cursor.fetchone()[0]

        # 고도 데이터 있는 NOTAM
        cursor.execute("""
            SELECT COUNT(*)
            FROM notams
            WHERE f_lower_limit IS NOT NULL AND g_upper_limit IS NOT NULL
        """)
        altitude_count = cursor.fetchone()[0]

        # 고도별 분포
        cursor.execute("""
            SELECT
                g_upper_limit,
                COUNT(*) as count
            FROM notams
            WHERE g_upper_limit IS NOT NULL
            GROUP BY g_upper_limit
            ORDER BY count DESC
            LIMIT 10
        """)
        altitude_dist = cursor.fetchall()

        conn.close()

        print(f"\n[INFO] 총 NOTAM: {total_count}개")
        print(f"[INFO] 고도 데이터 포함: {altitude_count}개 ({altitude_count/total_count*100:.1f}%)")

        if total_count < 500:
            print(f"[WARNING] NOTAM 개수가 예상보다 적습니다. (현재: {total_count}개)")
            print("[INFO] 더 긴 기간을 크롤링하거나 크롤링 간격을 조정하세요.")
        else:
            print(f"[OK] 충분한 NOTAM 데이터 수집 완료! ({total_count}개)")

        print(f"\n[INFO] 고도별 상위 10개 분포:")
        for alt, count in altitude_dist:
            fl_feet = int(alt) * 100 if alt.isdigit() else alt
            print(f"  {alt} ({fl_feet} ft): {count}개")

    except Exception as e:
        print(f"[ERROR] 결과 확인 중 오류: {e}")
        return False

    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = crawl_30_days()
    sys.exit(0 if success else 1)
