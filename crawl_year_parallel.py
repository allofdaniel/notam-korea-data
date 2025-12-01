#!/usr/bin/env python3
"""
연도별 NOTAM 병렬 크롤링
"""
from notam_crawler_api import NOTAMCrawlerAPI
from datetime import datetime
import pytz
import sys

def main():
    if len(sys.argv) < 2:
        print("사용법: python crawl_year_parallel.py <year>")
        sys.exit(1)
    
    year = int(sys.argv[1])
    current_year = datetime.now().year
    
    # 날짜 범위 설정
    if year == current_year:
        # 올해는 현재까지
        start_date = datetime(year, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
        end_date = datetime.now(pytz.UTC)
    else:
        # 과거 년도는 전체
        start_date = datetime(year, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
        end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=pytz.UTC)
    
    total_hours = int((end_date - start_date).total_seconds() / 3600)
    
    print("=" * 80)
    print(f"{year}년 NOTAM 크롤링")
    print("=" * 80)
    print(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"총 {total_hours:,}시간")
    
    # 연도별 DB 파일
    db_name = f'notam_{year}.db'
    crawler = NOTAMCrawlerAPI(db_name=db_name)
    
    try:
        # 국내 NOTAM
        print(f"\n[1/2] {year}년 국내 NOTAM 크롤링...")
        domestic = crawler.crawl_notam_api('domestic', start_date=start_date, end_date=end_date)

        print(f"\n국내 결과:")
        print(f"  발견: {domestic.get('records_found', 0):,}개")
        print(f"  저장: {domestic.get('records_saved', 0):,}개")

        # 국제 NOTAM
        print(f"\n[2/2] {year}년 국제 NOTAM 크롤링...")
        international = crawler.crawl_notam_api('international', start_date=start_date, end_date=end_date)
        
        print(f"\n국제 결과:")
        print(f"  발견: {international.get('records_found', 0):,}개")
        print(f"  저장: {international.get('records_saved', 0):,}개")
        
        total = domestic.get('records_saved', 0) + international.get('records_saved', 0)
        print(f"\n{year}년 총 {total:,}개 NOTAM 저장 완료!")
        print("=" * 80)
        
    finally:
        crawler.close()

if __name__ == "__main__":
    main()
