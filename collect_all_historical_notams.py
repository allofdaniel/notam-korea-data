#!/usr/bin/env python3
"""
2020년부터 현재까지 모든 NOTAM 데이터 수집 및 S3 저장
일주일 단위로 나눠서 수집
"""
import sys
import os
from datetime import datetime, timedelta
import time
import logging
import json
import boto3
from notam_crawler_api import NOTAMCrawlerAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoricalNOTAMCollector:
    """과거 NOTAM 데이터 전체 수집기"""

    def __init__(self, db_name='notam_historical.db', s3_bucket='notam-korea-data'):
        self.crawler = NOTAMCrawlerAPI(db_name=db_name)
        self.db_name = db_name
        self.s3_bucket = s3_bucket

        # S3 클라이언트
        self.s3 = boto3.client('s3', region_name='ap-southeast-2')

        # S3 버킷 생성 (없으면)
        try:
            self.s3.head_bucket(Bucket=s3_bucket)
            logger.info(f"✅ S3 버킷 존재: {s3_bucket}")
        except:
            try:
                self.s3.create_bucket(
                    Bucket=s3_bucket,
                    CreateBucketConfiguration={'LocationConstraint': 'ap-southeast-2'}
                )
                logger.info(f"✅ S3 버킷 생성: {s3_bucket}")
            except Exception as e:
                logger.warning(f"⚠️ S3 버킷 생성/확인 실패: {e}")

    def collect_week_range(self, start_date: datetime, end_date: datetime, week_num: int, total_weeks: int):
        """
        특정 일주일 기간의 NOTAM 수집

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            week_num: 현재 주차
            total_weeks: 전체 주차 수
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"📅 Week {week_num}/{total_weeks}: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"{'='*80}")

        hours = int((end_date - start_date).total_seconds() / 3600)

        collected = {'domestic': 0, 'international': 0}

        # 국내 NOTAM
        try:
            logger.info("🇰🇷 국내 NOTAM 수집 중...")
            domestic_result = self.crawler.crawl_notam_api('domestic', hours_back=hours)

            if domestic_result.get('status') == 'SUCCESS':
                collected['domestic'] = domestic_result.get('records_saved', 0)
                logger.info(f"  ✅ 국내: {collected['domestic']}개 수집")
            else:
                logger.error(f"  ❌ 국내 실패: {domestic_result.get('error')}")

            time.sleep(2)
        except Exception as e:
            logger.error(f"  ❌ 국내 수집 오류: {e}")

        # 국제 NOTAM
        try:
            logger.info("🌏 국제 NOTAM 수집 중...")
            intl_result = self.crawler.crawl_notam_api('international', hours_back=hours)

            if intl_result.get('status') == 'SUCCESS':
                collected['international'] = intl_result.get('records_saved', 0)
                logger.info(f"  ✅ 국제: {collected['international']}개 수집")
            else:
                logger.error(f"  ❌ 국제 실패: {intl_result.get('error')}")

            time.sleep(2)
        except Exception as e:
            logger.error(f"  ❌ 국제 수집 오류: {e}")

        total = collected['domestic'] + collected['international']
        logger.info(f"📊 Week {week_num} 합계: {total}개 (국내 {collected['domestic']}, 국제 {collected['international']})")

        return collected

    def upload_to_s3(self, file_path: str, s3_key: str):
        """
        파일을 S3에 업로드

        Args:
            file_path: 로컬 파일 경로
            s3_key: S3 객체 키
        """
        try:
            self.s3.upload_file(file_path, self.s3_bucket, s3_key)
            logger.info(f"☁️  S3 업로드 완료: s3://{self.s3_bucket}/{s3_key}")
            return True
        except Exception as e:
            logger.error(f"❌ S3 업로드 실패: {e}")
            return False

    def collect_all_data(self, start_year=2020, start_month=1, start_day=1):
        """
        지정된 시작일부터 현재까지 모든 NOTAM 데이터 수집

        Args:
            start_year: 시작 년도
            start_month: 시작 월
            start_day: 시작 일
        """
        logger.info(f"\n{'#'*80}")
        logger.info(f"🚀 과거 NOTAM 데이터 전체 수집 시작")
        logger.info(f"📅 기간: {start_year}-{start_month:02d}-{start_day:02d} ~ {datetime.now().strftime('%Y-%m-%d')}")
        logger.info(f"{'#'*80}\n")

        # 시작/종료 날짜
        start_date = datetime(start_year, start_month, start_day, 0, 0, 0)
        end_date = datetime.now()

        # 총 일수 및 주차 계산
        total_days = (end_date - start_date).days
        total_weeks = (total_days // 7) + 1

        logger.info(f"📊 총 기간: {total_days}일 ({total_weeks}주)")
        logger.info(f"⏱️  예상 소요시간: 약 {total_weeks * 0.5:.1f}분 (주당 30초 가정)\n")

        # 수집 통계
        total_collected = {'domestic': 0, 'international': 0}
        week_count = 0

        current_date = start_date

        # 일주일씩 반복
        while current_date < end_date:
            week_count += 1
            week_end = min(current_date + timedelta(days=7), end_date)

            # 해당 주 수집
            try:
                collected = self.collect_week_range(current_date, week_end, week_count, total_weeks)

                total_collected['domestic'] += collected['domestic']
                total_collected['international'] += collected['international']

                # 10주마다 DB를 S3에 백업
                if week_count % 10 == 0:
                    backup_key = f"backups/notam_historical_{current_date.strftime('%Y%m%d')}.db"
                    self.upload_to_s3(self.db_name, backup_key)

                # 진행률 표시
                progress = (week_count / total_weeks) * 100
                logger.info(f"📈 진행률: {progress:.1f}% ({week_count}/{total_weeks} weeks)")
                logger.info(f"📦 누적: {total_collected['domestic'] + total_collected['international']}개\n")

            except Exception as e:
                logger.error(f"❌ Week {week_count} 수집 실패: {e}")

            # 다음 주로 이동
            current_date = week_end

            # API 부하 방지
            time.sleep(3)

        # 최종 DB를 S3에 업로드
        logger.info(f"\n{'='*80}")
        logger.info("☁️  최종 데이터베이스 S3 업로드 중...")

        final_key = f"notam_historical_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        self.upload_to_s3(self.db_name, final_key)

        # 결과 요약
        logger.info(f"\n{'#'*80}")
        logger.info("✅ 전체 수집 완료!")
        logger.info(f"{'#'*80}")
        logger.info(f"📊 수집 통계:")
        logger.info(f"  - 총 주차: {week_count}주")
        logger.info(f"  - 국내 NOTAM: {total_collected['domestic']:,}개")
        logger.info(f"  - 국제 NOTAM: {total_collected['international']:,}개")
        logger.info(f"  - 전체 합계: {total_collected['domestic'] + total_collected['international']:,}개")
        logger.info(f"☁️  S3 버킷: s3://{self.s3_bucket}/{final_key}")
        logger.info(f"{'#'*80}\n")

        # 수집 보고서 생성
        report = {
            'collection_date': datetime.now().isoformat(),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_weeks': week_count,
            'total_days': total_days,
            'statistics': {
                'domestic': total_collected['domestic'],
                'international': total_collected['international'],
                'total': total_collected['domestic'] + total_collected['international']
            },
            's3_bucket': self.s3_bucket,
            's3_key': final_key
        }

        # 보고서를 JSON 파일로 저장
        report_file = f"collection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # 보고서도 S3에 업로드
        report_key = f"reports/{report_file}"
        self.upload_to_s3(report_file, report_key)

        return report

    def close(self):
        """리소스 정리"""
        if self.crawler:
            self.crawler.close()


def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description='과거 NOTAM 데이터 전체 수집 및 S3 저장')
    parser.add_argument('--start-year', type=int, default=2020, help='시작 년도 (기본: 2020)')
    parser.add_argument('--start-month', type=int, default=1, help='시작 월 (기본: 1)')
    parser.add_argument('--start-day', type=int, default=1, help='시작 일 (기본: 1)')
    parser.add_argument('--s3-bucket', type=str, default='notam-korea-data', help='S3 버킷 이름')

    args = parser.parse_args()

    collector = HistoricalNOTAMCollector(s3_bucket=args.s3_bucket)

    try:
        report = collector.collect_all_data(
            start_year=args.start_year,
            start_month=args.start_month,
            start_day=args.start_day
        )

        print("\n" + "="*80)
        print("✅ 수집 완료!")
        print("="*80)
        print(f"총 NOTAM: {report['statistics']['total']:,}개")
        print(f"S3 위치: s3://{report['s3_bucket']}/{report['s3_key']}")
        print("="*80)

        exit(0)

    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 중단됨")
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
