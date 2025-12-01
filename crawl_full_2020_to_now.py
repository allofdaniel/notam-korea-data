#!/usr/bin/env python3
"""
2020년 1월 1일부터 현재까지 모든 NOTAM 크롤링
"""
from notam_crawler_api import NOTAMCrawlerAPI
from datetime import datetime
import pytz

def main():
    print("=" * 80)
    print("전체 NOTAM 크롤링 (2020-01-01 ~ 현재)")
    print("=" * 80)

    # 2020-01-01부터 현재까지 계산
    start_date = datetime(2020, 1, 1, 0, 0, 0, tzinfo=pytz.timezone('UTC'))
    now = datetime.now(pytz.timezone('UTC'))

    total_days = (now - start_date).days
    hours = total_days * 24

    print(f"\n기간: {total_days}일 ({hours:,}시간)")
    print(f"예상: 수만 개 NOTAM")
    print(f"\n시작: 2020-01-01 00:00 UTC")
    print(f"종료: {now.strftime('%Y-%m-%d %H:%M UTC')}")

    crawler = NOTAMCrawlerAPI()

    try:
        # 국내 NOTAM
        print(f"\n[1/2] 국내 NOTAM 크롤링...")
        domestic = crawler.crawl_notam_api('domestic', hours_back=hours)

        print(f"\n국내 결과:")
        print(f"  발견: {domestic.get('records_found', 0):,}개")
        print(f"  저장: {domestic.get('records_saved', 0):,}개")

        # 국제 NOTAM
        print(f"\n[2/2] 국제 NOTAM 크롤링...")
        international = crawler.crawl_notam_api('international', hours_back=hours)

        print(f"\n국제 결과:")
        print(f"  발견: {international.get('records_found', 0):,}개")
        print(f"  저장: {international.get('records_saved', 0):,}개")

        total = domestic.get('records_saved', 0) + international.get('records_saved', 0)
        print(f"\n총 {total:,}개 NOTAM 저장!")
        print("=" * 80)

    finally:
        crawler.close()

if __name__ == "__main__":
    main()
