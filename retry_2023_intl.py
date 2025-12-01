from notam_crawler_api import NOTAMCrawlerAPI
from datetime import datetime
import pytz

start = datetime(2023, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
end = datetime(2023, 12, 31, 23, 59, 59, tzinfo=pytz.UTC)

crawler = NOTAMCrawlerAPI(db_name='notam_2023.db')
print('2023년 국제 NOTAM 재크롤링 시작...')
result = crawler.crawl_notam_api('international', start_date=start, end_date=end)
print(f"결과: {result.get('records_found', 0):,}개 발견, {result.get('records_saved', 0):,}개 저장")
crawler.close()
