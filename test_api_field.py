from notam_crawler_api import NOTAMCrawlerAPI

crawler = NOTAMCrawlerAPI()

# 1페이지 1개만 가져오기
notams, error = crawler.crawl_notam_api('domestic', hours_back=720)

if notams:
    print(f"\n수집된 NOTAM 수: {len(notams)}")
else:
    print("\n수집된 NOTAM이 없습니다!")

crawler.close()
