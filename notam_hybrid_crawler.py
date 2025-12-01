"""
NOTAM 하이브리드 크롤러 - API 우선, Selenium 백업
작성일: 2025-11-11
전략: API 방식을 먼저 시도하고, 실패 시 Selenium 크롤러로 fallback
"""

import logging
import sys
import os
from typing import Dict, Optional
from datetime import datetime

# Windows 한국어 환경 인코딩 설정
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'detach'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    except:
        pass  # 이미 설정되어 있음

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NOTAMHybridCrawler:
    """
    NOTAM 하이브리드 크롤러
    - 우선순위 1: API 직접 호출 (빠르고 안정적)
    - 우선순위 2: Selenium 크롤러 (백업용)
    """

    def __init__(self, db_name='notam_realtime.db'):
        """
        초기화

        Args:
            db_name (str): SQLite 데이터베이스 파일명
        """
        self.db_name = db_name
        self.api_crawler = None
        self.selenium_crawler = None

        logger.info("[OK] NOTAM 하이브리드 크롤러 초기화")

    def _init_api_crawler(self):
        """API 크롤러 초기화 (lazy loading)"""
        if self.api_crawler is None:
            try:
                from notam_crawler_api import NOTAMCrawlerAPI
                self.api_crawler = NOTAMCrawlerAPI(db_name=self.db_name)
                logger.info("[OK] API 크롤러 로드 완료")
            except Exception as e:
                logger.error(f"[ERROR] API 크롤러 로드 실패: {e}")
                raise

        return self.api_crawler

    def _init_selenium_crawler(self):
        """Selenium 크롤러 초기화 (lazy loading)"""
        if self.selenium_crawler is None:
            try:
                from notam_crawler import NOTAMCrawler
                self.selenium_crawler = NOTAMCrawler(
                    db_name=self.db_name,
                    headless=True  # 프로덕션에서는 헤드리스 모드
                )
                logger.info("[OK] Selenium 크롤러 로드 완료")
            except Exception as e:
                logger.error(f"[ERROR] Selenium 크롤러 로드 실패: {e}")
                raise

        return self.selenium_crawler

    def crawl_notam(self, data_source: str = 'domestic',
                   hours_back: int = 24,
                   force_selenium: bool = False) -> Dict:
        """
        NOTAM 크롤링 실행 (하이브리드)

        Args:
            data_source (str): 'domestic' 또는 'international'
            hours_back (int): 과거 몇 시간부터 검색
            force_selenium (bool): True이면 Selenium 강제 사용

        Returns:
            Dict: 크롤링 결과
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"[START] {data_source.upper()} NOTAM 하이브리드 크롤링")
        logger.info(f"[INFO] 검색 범위: 최근 {hours_back}시간")
        logger.info(f"{'='*70}\n")

        result = {
            'status': 'FAILED',
            'method': None,
            'records_found': 0,
            'records_saved': 0,
            'execution_time': 0,
            'error': None
        }

        # Selenium 강제 모드
        if force_selenium:
            logger.info("[MODE] Selenium 강제 모드")
            return self._crawl_with_selenium(data_source, hours_back, result)

        # 우선순위 1: API 크롤러 시도
        logger.info("[ATTEMPT 1] API 크롤러 시도...")
        try:
            api_crawler = self._init_api_crawler()
            api_result = api_crawler.crawl_notam_api(data_source, hours_back)

            # API 성공
            if api_result.get('status') == 'SUCCESS':
                result.update({
                    'status': 'SUCCESS',
                    'method': 'API',
                    'records_found': api_result.get('records_found', 0),
                    'records_saved': api_result.get('records_saved', 0),
                    'execution_time': api_result.get('execution_time', 0)
                })
                logger.info(f"[SUCCESS] API 크롤링 성공: {result['records_found']}개 발견")
                return result

            # API 실패 - Selenium으로 fallback
            logger.warning(f"[WARN] API 크롤링 실패: {api_result.get('error', 'Unknown error')}")
            logger.info("[ATTEMPT 2] Selenium 크롤러로 fallback...")

        except Exception as e:
            logger.error(f"[ERROR] API 크롤러 오류: {e}")
            logger.info("[ATTEMPT 2] Selenium 크롤러로 fallback...")

        # 우선순위 2: Selenium 크롤러 시도
        return self._crawl_with_selenium(data_source, hours_back, result)

    def _crawl_with_selenium(self, data_source: str, hours_back: int, result: Dict) -> Dict:
        """
        Selenium 크롤러로 크롤링 실행

        Args:
            data_source (str): 'domestic' 또는 'international'
            hours_back (int): 과거 몇 시간부터 검색
            result (Dict): 결과 딕셔너리

        Returns:
            Dict: 업데이트된 결과
        """
        try:
            selenium_crawler = self._init_selenium_crawler()
            selenium_result = selenium_crawler.crawl_notam(data_source, hours_back)

            # Selenium 성공
            if selenium_result.get('status') == 'SUCCESS':
                result.update({
                    'status': 'SUCCESS',
                    'method': 'SELENIUM',
                    'records_found': selenium_result.get('records_found', 0),
                    'records_saved': selenium_result.get('records_saved', 0),
                    'execution_time': selenium_result.get('execution_time', 0)
                })
                logger.info(f"[SUCCESS] Selenium 크롤링 성공: {result['records_found']}개 발견")
            else:
                result['error'] = selenium_result.get('error', 'Unknown error')
                logger.error(f"[ERROR] Selenium 크롤링 실패: {result['error']}")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"[ERROR] Selenium 크롤러 오류: {e}")

        return result

    def crawl_all(self, hours_back: int = 24) -> Dict:
        """
        국내 + 국제 NOTAM 전체 크롤링

        Args:
            hours_back (int): 과거 몇 시간부터 검색

        Returns:
            Dict: 전체 크롤링 결과
        """
        logger.info("\n" + "="*70)
        logger.info("[START] 전체 NOTAM 크롤링 (국내 + 국제)")
        logger.info("="*70 + "\n")

        # 국내 NOTAM
        domestic_result = self.crawl_notam('domestic', hours_back)

        # 국제 NOTAM
        international_result = self.crawl_notam('international', hours_back)

        # 통합 결과
        total_found = domestic_result['records_found'] + international_result['records_found']
        total_saved = domestic_result['records_saved'] + international_result['records_saved']
        total_time = domestic_result['execution_time'] + international_result['execution_time']

        logger.info("\n" + "="*70)
        logger.info("[SUMMARY] 전체 크롤링 결과")
        logger.info("="*70)
        logger.info(f"국내 NOTAM: {domestic_result['records_found']}개 (방법: {domestic_result['method']})")
        logger.info(f"국제 NOTAM: {international_result['records_found']}개 (방법: {international_result['method']})")
        logger.info(f"총 발견: {total_found}개")
        logger.info(f"총 저장: {total_saved}개")
        logger.info(f"총 시간: {total_time:.2f}초")
        logger.info("="*70 + "\n")

        return {
            'domestic': domestic_result,
            'international': international_result,
            'total': {
                'records_found': total_found,
                'records_saved': total_saved,
                'execution_time': total_time
            }
        }

    def close(self):
        """리소스 정리"""
        if self.api_crawler:
            try:
                self.api_crawler.close()
            except:
                pass

        if self.selenium_crawler:
            try:
                # Selenium 크롤러는 자동으로 드라이버를 닫음
                pass
            except:
                pass


def main():
    """메인 실행 함수"""
    crawler = NOTAMHybridCrawler()

    try:
        # 전체 크롤링 (24시간 범위)
        results = crawler.crawl_all(hours_back=24)

        # 성공 여부 확인
        domestic_ok = results['domestic']['status'] == 'SUCCESS'
        intl_ok = results['international']['status'] == 'SUCCESS'

        if domestic_ok and intl_ok:
            print("\n✅ 전체 크롤링 성공!")
            exit(0)
        elif domestic_ok or intl_ok:
            print("\n⚠️  부분 성공 (일부 크롤링 실패)")
            exit(1)
        else:
            print("\n❌ 전체 크롤링 실패")
            exit(2)

    except Exception as e:
        logger.error(f"[FATAL] 크롤러 실행 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        exit(3)
    finally:
        crawler.close()


if __name__ == '__main__':
    main()
