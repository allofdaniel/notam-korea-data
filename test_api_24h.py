"""API 크롤러 24시간 테스트"""
from notam_crawler_api import NOTAMCrawlerAPI

crawler = NOTAMCrawlerAPI()

print("24시간 범위로 NOTAM 크롤링 테스트...")
print()

# 국내 NOTAM (24시간)
result_domestic = crawler.crawl_notam_api('domestic', hours_back=24)
print(f"\n국내 NOTAM: {result_domestic}")

# 국제 NOTAM (24시간)
result_intl = crawler.crawl_notam_api('international', hours_back=24)
print(f"\n국제 NOTAM: {result_intl}")

crawler.close()
