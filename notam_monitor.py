"""
NOTAM 모니터링 시스템 - 크롤링 + 변경 감지 통합
작성일: 2025-11-11
기능:
  - 하이브리드 크롤링 (API 우선, Selenium 백업)
  - 자동 변경 감지
  - 변경 이력 로그
  - 통계 및 알림
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, Optional

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


class NOTAMMonitor:
    """
    NOTAM 통합 모니터링 시스템
    - 크롤링 + 변경 감지 + 알림
    """

    def __init__(self, db_name='notam_realtime.db'):
        """
        초기화

        Args:
            db_name (str): SQLite 데이터베이스 파일명
        """
        self.db_name = db_name
        self.crawler = None
        self.detector = None

        logger.info("\n" + "="*70)
        logger.info("NOTAM 통합 모니터링 시스템")
        logger.info("="*70)
        logger.info("[OK] 시스템 초기화 완료\n")

    def _init_crawler(self):
        """크롤러 초기화 (lazy loading)"""
        if self.crawler is None:
            from notam_hybrid_crawler import NOTAMHybridCrawler
            self.crawler = NOTAMHybridCrawler(db_name=self.db_name)

        return self.crawler

    def _init_detector(self):
        """변경 감지기 초기화 (lazy loading)"""
        if self.detector is None:
            from notam_change_detector import NOTAMChangeDetector
            self.detector = NOTAMChangeDetector(db_name=self.db_name)

        return self.detector

    def monitor_single(self, data_source: str = 'domestic',
                      hours_back: int = 24,
                      enable_change_detection: bool = True) -> Dict:
        """
        단일 데이터 소스 모니터링

        Args:
            data_source (str): 'domestic' 또는 'international'
            hours_back (int): 과거 몇 시간부터 검색
            enable_change_detection (bool): 변경 감지 활성화 여부

        Returns:
            Dict: 모니터링 결과
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"[START] {data_source.upper()} NOTAM 모니터링")
        logger.info(f"[INFO] 검색 범위: 최근 {hours_back}시간")
        logger.info(f"[INFO] 변경 감지: {'활성화' if enable_change_detection else '비활성화'}")
        logger.info(f"{'='*70}\n")

        result = {
            'data_source': data_source,
            'status': 'FAILED',
            'crawl_result': None,
            'change_result': None,
            'timestamp': datetime.now().isoformat()
        }

        # 1. 크롤링 실행
        try:
            crawler = self._init_crawler()
            crawl_result = crawler.crawl_notam(data_source, hours_back)
            result['crawl_result'] = crawl_result

            if crawl_result['status'] != 'SUCCESS':
                logger.error(f"[ERROR] 크롤링 실패: {crawl_result.get('error', 'Unknown')}")
                return result

            logger.info(f"[OK] 크롤링 완료: {crawl_result['records_found']}개 발견\n")

        except Exception as e:
            logger.error(f"[ERROR] 크롤링 오류: {e}")
            result['error'] = str(e)
            return result

        # 2. 변경 감지 (옵션)
        if enable_change_detection and crawl_result['records_found'] > 0:
            try:
                # 현재 크롤링한 데이터를 가져오기
                current_notams = self._get_current_notams(data_source)

                if current_notams:
                    detector = self._init_detector()

                    # 변경 감지
                    changes = detector.detect_changes(current_notams, data_source)

                    # 변경 로그 저장
                    change_result = detector.process_changes(
                        changes,
                        data_source=data_source,
                        crawl_batch_id=None
                    )

                    result['change_result'] = {
                        'status': change_result['status'],
                        'new': len(changes['new']),
                        'updated': len(changes['updated']),
                        'deleted': len(changes['deleted']),
                        'unchanged': changes['unchanged'],
                        'logs_saved': change_result['saved_count']
                    }

                    logger.info(f"[OK] 변경 감지 완료")
                    logger.info(f"  신규: {len(changes['new'])}개")
                    logger.info(f"  업데이트: {len(changes['updated'])}개")
                    logger.info(f"  삭제: {len(changes['deleted'])}개\n")

            except Exception as e:
                logger.error(f"[ERROR] 변경 감지 오류: {e}")
                result['change_result'] = {'status': 'FAILED', 'error': str(e)}

        result['status'] = 'SUCCESS'
        return result

    def _get_current_notams(self, data_source: str):
        """현재 DB의 NOTAM 데이터 가져오기"""
        import sqlite3

        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM notam_records WHERE data_source = ?",
            (data_source,)
        )

        notams = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return notams

    def monitor_all(self, hours_back: int = 24,
                   enable_change_detection: bool = True) -> Dict:
        """
        전체 모니터링 (국내 + 국제)

        Args:
            hours_back (int): 과거 몇 시간부터 검색
            enable_change_detection (bool): 변경 감지 활성화 여부

        Returns:
            Dict: 전체 모니터링 결과
        """
        logger.info("\n" + "="*70)
        logger.info("[START] 전체 NOTAM 모니터링 (국내 + 국제)")
        logger.info("="*70 + "\n")

        # 국내 모니터링
        domestic_result = self.monitor_single('domestic', hours_back, enable_change_detection)

        # 국제 모니터링
        international_result = self.monitor_single('international', hours_back, enable_change_detection)

        # 통합 결과
        logger.info("\n" + "="*70)
        logger.info("[SUMMARY] 전체 모니터링 결과")
        logger.info("="*70)

        # 국내 요약
        logger.info(f"\n국내 NOTAM:")
        if domestic_result['crawl_result']:
            cr = domestic_result['crawl_result']
            logger.info(f"  크롤링: {cr['records_found']}개 발견 (방법: {cr['method']})")

        if domestic_result.get('change_result'):
            ch = domestic_result['change_result']
            logger.info(f"  변경: 신규 {ch['new']}개, 업데이트 {ch['updated']}개, 삭제 {ch['deleted']}개")

        # 국제 요약
        logger.info(f"\n국제 NOTAM:")
        if international_result['crawl_result']:
            cr = international_result['crawl_result']
            logger.info(f"  크롤링: {cr['records_found']}개 발견 (방법: {cr['method']})")

        if international_result.get('change_result'):
            ch = international_result['change_result']
            logger.info(f"  변경: 신규 {ch['new']}개, 업데이트 {ch['updated']}개, 삭제 {ch['deleted']}개")

        logger.info("\n" + "="*70 + "\n")

        return {
            'domestic': domestic_result,
            'international': international_result,
            'timestamp': datetime.now().isoformat()
        }

    def get_statistics(self, hours: int = 24) -> Dict:
        """
        통계 조회

        Args:
            hours (int): 최근 몇 시간

        Returns:
            Dict: 통계 정보
        """
        detector = self._init_detector()

        domestic_stats = detector.get_change_stats('domestic', hours)
        intl_stats = detector.get_change_stats('international', hours)

        return {
            'period_hours': hours,
            'domestic': domestic_stats,
            'international': intl_stats
        }

    def close(self):
        """리소스 정리"""
        if self.crawler:
            try:
                self.crawler.close()
            except:
                pass

        if self.detector:
            try:
                self.detector.close()
            except:
                pass


def main():
    """메인 실행 함수"""
    monitor = NOTAMMonitor()

    try:
        # 전체 모니터링 실행 (24시간 범위, 변경 감지 활성화)
        results = monitor.monitor_all(hours_back=24, enable_change_detection=True)

        # 통계 조회
        stats = monitor.get_statistics(hours=24)

        print("\n" + "="*70)
        print("📊 최근 24시간 변경 통계")
        print("="*70)
        print(f"\n국내 NOTAM:")
        for change_type, count in stats['domestic'].items():
            print(f"  {change_type}: {count}개")

        print(f"\n국제 NOTAM:")
        for change_type, count in stats['international'].items():
            print(f"  {change_type}: {count}개")

        print("\n" + "="*70)

        # 성공 여부 확인
        domestic_ok = results['domestic']['status'] == 'SUCCESS'
        intl_ok = results['international']['status'] == 'SUCCESS'

        if domestic_ok and intl_ok:
            print("\n✅ 전체 모니터링 성공!")
            exit(0)
        elif domestic_ok or intl_ok:
            print("\n⚠️  부분 성공 (일부 모니터링 실패)")
            exit(1)
        else:
            print("\n❌ 전체 모니터링 실패")
            exit(2)

    except Exception as e:
        logger.error(f"[FATAL] 모니터링 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        exit(3)

    finally:
        monitor.close()


if __name__ == '__main__':
    main()
