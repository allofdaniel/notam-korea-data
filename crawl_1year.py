#!/usr/bin/env python3
"""
1년치 NOTAM 크롤링 (2024-11-19 ~ 2025-11-19)
"""
from notam_crawler_api import NOTAMCrawlerAPI
from datetime import datetime, timedelta
import pytz

def main():
    print("=" * 80)
    print("1년치 NOTAM 크롤링 (2024-11-19 ~ 2025-11-19)")
    print("=" * 80)

    # 1년 = 365일 = 8760시간
    hours = 365 * 24

    print(f"\n기간: {hours}시간 (365일)")
    print(f"예상 개수: 15,000+ 개")

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
