#!/usr/bin/env python3
"""
7일 NOTAM 데이터 크롤링
"""
from notam_crawler_api import NOTAMCrawlerAPI

def main():
    print("=" * 80)
    print("7일 NOTAM 크롤링 시작 (168시간)")
    print("=" * 80)

    crawler = NOTAMCrawlerAPI()

    try:
        # 7일 = 168시간
        hours = 168

        print(f"\n[1] 국내 NOTAM 크롤링 ({hours}시간)...")
        domestic_result = crawler.crawl_notam_api('domestic', hours_back=hours)

        print(f"\n[결과] 국내 NOTAM:")
        print(f"  - 상태: {domestic_result['status']}")
        print(f"  - 발견: {domestic_result.get('records_found', 0)}개")
        print(f"  - 저장: {domestic_result.get('records_saved', 0)}개")

        print(f"\n[2] 국제 NOTAM 크롤링 ({hours}시간)...")
        international_result = crawler.crawl_notam_api('international', hours_back=hours)

        print(f"\n[결과] 국제 NOTAM:")
        print(f"  - 상태: {international_result['status']}")
        print(f"  - 발견: {international_result.get('records_found', 0)}개")
        print(f"  - 저장: {international_result.get('records_saved', 0)}개")

        total = domestic_result.get('records_saved', 0) + international_result.get('records_saved', 0)
        print(f"\n[전체] 총 {total}개 NOTAM 저장 완료!")
        print("=" * 80)

    finally:
        crawler.close()

if __name__ == "__main__":
    main()
