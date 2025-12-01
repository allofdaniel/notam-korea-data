#!/usr/bin/env python3
"""
NOTAM 과거 데이터 수집기 - 3년치 데이터 다운로드
시간별로 나눠서 수집하여 API 부하 최소화
"""

import sys
import os
from datetime import datetime, timedelta
from notam_crawler_api import NOTAMCrawlerAPI
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NOTAMHistoricalLoader:
    """3년치 NOTAM 과거 데이터 수집"""

    def __init__(self, db_name='notam_realtime.db'):
        self.crawler = NOTAMCrawlerAPI(db_name=db_name)

    def load_historical_data(self, years_back=3, chunk_days=30):
        """
        과거 N년치 NOTAM 데이터 수집

        Args:
            years_back: 과거 몇 년치 데이터
            chunk_days: 한 번에 수집할 기간 (일)
        """
        logger.info(f"=" * 70)
        logger.info(f"과거 {years_back}년치 NOTAM 데이터 수집 시작")
        logger.info(f"=" * 70)

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=years_back * 365)

        total_collected = 0
        current_date = start_date

        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=chunk_days), end_date)
            days_diff = (chunk_end - current_date).days
            hours_back = days_diff * 24

            logger.info(f"\n기간: {current_date.strftime('%Y-%m-%d')} ~ {chunk_end.strftime('%Y-%m-%d')}")
            logger.info(f"수집 범위: {hours_back}시간")

            try:
                # 국내 NOTAM 수집
                domestic_result = self.crawler.crawl_notam_api('domestic', hours_back=hours_back)
                if domestic_result.get('status') == 'SUCCESS':
                    count = domestic_result.get('records_saved', 0)
                    total_collected += count
                    logger.info(f"✅ 국내 NOTAM: {count}개 수집")

                time.sleep(2)  # API 부하 방지

                # 국제 NOTAM 수집
                intl_result = self.crawler.crawl_notam_api('international', hours_back=hours_back)
                if intl_result.get('status') == 'SUCCESS':
                    count = intl_result.get('records_saved', 0)
                    total_collected += count
                    logger.info(f"✅ 국제 NOTAM: {count}개 수집")

                time.sleep(2)  # API 부하 방지

            except Exception as e:
                logger.error(f"❌ 수집 실패: {e}")

            current_date = chunk_end

        logger.info(f"\n" + "=" * 70)
        logger.info(f"✅ 과거 데이터 수집 완료!")
        logger.info(f"총 수집: {total_collected}개 NOTAM")
        logger.info(f"=" * 70)

        return total_collected


def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description='NOTAM 과거 데이터 수집')
    parser.add_argument('--years', type=int, default=3, help='과거 몇 년치 (기본: 3년)')
    parser.add_argument('--chunk-days', type=int, default=30, help='한 번에 수집할 기간 (기본: 30일)')

    args = parser.parse_args()

    loader = NOTAMHistoricalLoader()

    try:
        total = loader.load_historical_data(
            years_back=args.years,
            chunk_days=args.chunk_days
        )

        print(f"\n✅ 성공: {total}개 NOTAM 수집 완료")
        exit(0)

    except Exception as e:
        print(f"\n❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        loader.crawler.close()


if __name__ == '__main__':
    main()
