#!/usr/bin/env python3
"""
전체 NOTAM 히스토리 크롤링
2020년 1월 1일 ~ 현재까지 모든 NOTAM 수집
"""
import sys
import sqlite3
from datetime import datetime, timedelta
import pytz
from notam_crawler_api import NOTAMCrawlerAPI

def crawl_full_history():
    """2020년부터 현재까지 전체 NOTAM 크롤링"""
    print("=" * 80)
    print("전체 NOTAM 히스토리 크롤링")
    print("=" * 80)

    # 시간 설정
    utc_now = datetime.now(pytz.timezone('UTC'))

    # 2020년 1월 1일부터 현재까지
    start_date = datetime(2020, 1, 1, 0, 0, 0, tzinfo=pytz.timezone('UTC'))

    total_days = (utc_now - start_date).days
    total_hours = total_days * 24

    print(f"\n크롤링 기간:")
    print(f"  시작: {start_date.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  종료: {utc_now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  기간: {total_days}일 ({total_hours}시간)")
    print(f"\n⚠️  예상 시간: 10-30분 (대용량 데이터)")

    # 사용자 확인
    response = input("\n계속하시겠습니까? (y/n): ")
    if response.lower() != 'y':
        print("취소되었습니다.")
        return False

    # 크롤러 초기화
    crawler = NOTAMCrawlerAPI()

    print("\n" + "=" * 80)
    print("크롤링 시작")
    print("=" * 80)

    try:
        # 국내 NOTAM 크롤링
        print(f"\n[1/2] 국내 NOTAM 크롤링 ({total_hours}시간)...")
        domestic_result = crawler.crawl_notam_api('domestic', hours_back=total_hours)

        print(f"\n국내 결과:")
        print(f"  상태: {domestic_result['status']}")
        print(f"  발견: {domestic_result.get('records_found', 0):,}개")
        print(f"  저장: {domestic_result.get('records_saved', 0):,}개")

        # 국제 NOTAM 크롤링
        print(f"\n[2/2] 국제 NOTAM 크롤링 ({total_hours}시간)...")
        international_result = crawler.crawl_notam_api('international', hours_back=total_hours)

        print(f"\n국제 결과:")
        print(f"  상태: {international_result['status']}")
        print(f"  발견: {international_result.get('records_found', 0):,}개")
        print(f"  저장: {international_result.get('records_saved', 0):,}개")

        # 최종 결과
        total_saved = domestic_result.get('records_saved', 0) + international_result.get('records_saved', 0)

        print("\n" + "=" * 80)
        print("크롤링 완료!")
        print("=" * 80)
        print(f"총 {total_saved:,}개 NOTAM 저장 완료")

        # DB 통계
        conn = sqlite3.connect('notam_realtime.db')
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM notams")
        db_total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM notams WHERE series_type='E'")
        e_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM notams WHERE series_type='D'")
        d_count = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(b_start_time), MAX(b_start_time) FROM notams")
        date_range = cursor.fetchone()

        conn.close()

        print(f"\nDB 통계:")
        print(f"  총 NOTAM: {db_total:,}개")
        print(f"  E 시리즈: {e_count:,}개")
        print(f"  D 시리즈: {d_count:,}개")
        print(f"  날짜 범위: {date_range[0]} ~ {date_range[1]}")

        return True

    except Exception as e:
        print(f"\n[ERROR] 크롤링 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        crawler.close()

if __name__ == "__main__":
    success = crawl_full_history()
    sys.exit(0 if success else 1)
