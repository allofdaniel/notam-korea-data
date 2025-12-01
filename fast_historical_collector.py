#!/usr/bin/env python3
"""
고속 NOTAM 수집기 - 1년 단위로 페이지네이션 적용
2020년부터 현재까지 모든 국내/국제 NOTAM 수집
"""
import sys
import time
import logging
from datetime import datetime, timedelta
from notam_crawler_api import NOTAMCrawlerAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FastHistoricalCollector:
    """1년 단위 고속 NOTAM 수집기"""

    def __init__(self, db_name='notam_historical.db'):
        self.crawler = NOTAMCrawlerAPI(db_name=db_name)
        self.db_name = db_name

    def collect_year_range(self, year: int, data_source: str):
        """
        특정 연도의 모든 NOTAM 수집 (페이지네이션 자동 적용)

        Args:
            year: 수집할 연도 (예: 2020)
            data_source: 'domestic' 또는 'international'

        Returns:
            dict: 수집 결과 {'success': bool, 'records': int}
        """
        # 1년 = 365일 = 8760시간
        hours_in_year = 8760

        logger.info(f"\n{'='*80}")
        logger.info(f"📅 {year}년 {data_source.upper()} NOTAM 수집 시작...")
        logger.info(f"{'='*80}")

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                result = self.crawler.crawl_notam_api(
                    data_source=data_source,
                    hours_back=hours_in_year
                )

                if result.get('status') == 'SUCCESS':
                    records = result.get('records_saved', 0)
                    logger.info(f"✅ {year}년 {data_source}: {records}개 수집 완료!")
                    return {'success': True, 'records': records}
                else:
                    error = result.get('error', 'Unknown error')
                    logger.error(f"❌ 실패: {error}")
                    retry_count += 1

                    if retry_count < max_retries:
                        wait_time = 5 * retry_count
                        logger.info(f"⏳ {wait_time}초 후 재시도... ({retry_count}/{max_retries})")
                        time.sleep(wait_time)

            except Exception as e:
                logger.error(f"❌ 오류: {e}")
                retry_count += 1

                if retry_count < max_retries:
                    wait_time = 5 * retry_count
                    logger.info(f"⏳ {wait_time}초 후 재시도... ({retry_count}/{max_retries})")
                    time.sleep(wait_time)

        logger.error(f"❌ {year}년 {data_source} 수집 최종 실패 (재시도 {max_retries}회 초과)")
        return {'success': False, 'records': 0}

    def collect_all(self, start_year=2020, end_year=None):
        """
        시작 연도부터 종료 연도까지 모든 NOTAM 수집

        Args:
            start_year: 시작 연도 (기본: 2020)
            end_year: 종료 연도 (기본: 현재 연도)
        """
        if end_year is None:
            end_year = datetime.now().year

        years = list(range(start_year, end_year + 1))

        logger.info(f"\n{'#'*80}")
        logger.info(f"🚀 고속 NOTAM 전체 수집 시작")
        logger.info(f"📅 기간: {start_year}년 ~ {end_year}년 ({len(years)}년)")
        logger.info(f"📊 예상 시간: 약 {len(years) * 2}분 (1년당 2분 가정)")
        logger.info(f"{'#'*80}\n")

        total_stats = {
            'domestic': 0,
            'international': 0,
            'years_completed': 0,
            'years_failed': []
        }

        for idx, year in enumerate(years, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"📆 {year}년 수집 중... ({idx}/{len(years)})")
            logger.info(f"{'='*80}")

            # 국내 NOTAM 수집
            domestic_result = self.collect_year_range(year, 'domestic')
            total_stats['domestic'] += domestic_result['records']

            # API 부하 방지
            time.sleep(2)

            # 국제 NOTAM 수집
            intl_result = self.collect_year_range(year, 'international')
            total_stats['international'] += intl_result['records']

            # 결과 확인
            if domestic_result['success'] and intl_result['success']:
                total_stats['years_completed'] += 1
                year_total = domestic_result['records'] + intl_result['records']
                logger.info(f"\n✅ {year}년 완료: {year_total}개 (국내 {domestic_result['records']}, 국제 {intl_result['records']})")
            else:
                total_stats['years_failed'].append(year)
                logger.warning(f"\n⚠️ {year}년 일부 실패")

            # 진행률 표시
            progress = (idx / len(years)) * 100
            total_collected = total_stats['domestic'] + total_stats['international']
            logger.info(f"\n📈 전체 진행률: {progress:.1f}% ({idx}/{len(years)} 년)")
            logger.info(f"📦 누적 수집: {total_collected:,}개")

            # API 부하 방지
            time.sleep(3)

        # 최종 결과
        logger.info(f"\n{'#'*80}")
        logger.info("✅ 전체 수집 완료!")
        logger.info(f"{'#'*80}")
        logger.info(f"📊 수집 통계:")
        logger.info(f"  - 완료된 연도: {total_stats['years_completed']}/{len(years)}년")
        logger.info(f"  - 국내 NOTAM: {total_stats['domestic']:,}개")
        logger.info(f"  - 국제 NOTAM: {total_stats['international']:,}개")
        logger.info(f"  - 전체 합계: {total_stats['domestic'] + total_stats['international']:,}개")

        if total_stats['years_failed']:
            logger.warning(f"  - 실패한 연도: {', '.join(map(str, total_stats['years_failed']))}")

        logger.info(f"💾 저장 위치: {self.db_name}")
        logger.info(f"{'#'*80}\n")

        return total_stats

    def close(self):
        """리소스 정리"""
        if self.crawler:
            self.crawler.close()


def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description='고속 NOTAM 전체 수집 (1년 단위)')
    parser.add_argument('--start-year', type=int, default=2020, help='시작 연도 (기본: 2020)')
    parser.add_argument('--end-year', type=int, default=None, help='종료 연도 (기본: 현재 연도)')
    parser.add_argument('--db-name', type=str, default='notam_historical.db', help='DB 파일명')

    args = parser.parse_args()

    collector = FastHistoricalCollector(db_name=args.db_name)

    try:
        stats = collector.collect_all(start_year=args.start_year, end_year=args.end_year)

        # 성공 여부 확인
        total_collected = stats['domestic'] + stats['international']
        if total_collected > 0:
            print(f"\n✅ 성공! 총 {total_collected:,}개 NOTAM 수집 완료")
            exit(0)
        else:
            print("\n❌ 수집 실패 - 데이터 없음")
            exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
        exit(1)

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

    finally:
        collector.close()


if __name__ == '__main__':
    main()
