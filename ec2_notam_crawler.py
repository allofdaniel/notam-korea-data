#!/usr/bin/env python3
"""
EC2 NOTAM 크롤러
- AIM 포털에서 국내 NOTAM 수집
- DynamoDB에 저장
- S3에 백업

작성일: 2025-11-13
실행: cron (5분마다)
"""

import boto3
import requests
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# AWS 설정
AWS_REGION = 'ap-southeast-2'
DYNAMODB_TABLE = 'NOTAM_Records'
S3_BUCKET = 'notam-backup'

# AIM 포털 설정
AIM_BASE_URL = 'https://aim.koca.go.kr'
AIM_API_URL = f'{AIM_BASE_URL}/xNotam/searchAllNotam.do'

# 국내 공항 ICAO 코드 (18개)
DOMESTIC_AIRPORTS = [
    'RKSI',  # 인천
    'RKSS',  # 김포
    'RKPC',  # 제주
    'RKPK',  # 김해
    'RKTU',  # 청주
    'RKTN',  # 대구
    'RKJY',  # 여수
    'RKJJ',  # 광주
    'RKNY',  # 양양
    'RKTH',  # 포항
    'RKPU',  # 울산
    'RKTI',  # 군산
    'RKTL',  # 사천
    'RKNW',  # 원주
    'RKJB',  # 무안
    'RKSM',  # 서울공항
    'RKSO',  # 수원
    'RKSG'   # 성남
]

# NOTAM 시리즈
NOTAM_SERIES = ['A', 'C', 'D', 'E', 'G', 'Z', 'SNOWTAM']


class EC2NOTAMCrawler:
    """EC2용 NOTAM 크롤러"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': f'{AIM_BASE_URL}/aip/index.do',
            'Origin': AIM_BASE_URL,
            'X-Requested-With': 'XMLHttpRequest'
        })

        self.dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        self.table = self.dynamodb.Table(DYNAMODB_TABLE)
        self.s3 = boto3.client('s3', region_name=AWS_REGION)

    def crawl_domestic_notams(self, hours_back: int = 2) -> Dict:
        """국내 NOTAM 크롤링"""

        print(f"{'='*60}")
        print(f"EC2 NOTAM 크롤러 시작")
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        all_notams = []
        saved_count = 0
        error_count = 0

        # 각 공항별로 크롤링
        for airport in DOMESTIC_AIRPORTS:
            print(f"[크롤링] {airport}...", end=' ')

            try:
                notams = self._fetch_notams(airport, start_time, end_time)
                all_notams.extend(notams)
                print(f"✅ {len(notams)}개")

            except Exception as e:
                print(f"❌ 오류: {e}")
                error_count += 1

        print(f"\n총 수집: {len(all_notams)}개")

        # DynamoDB에 저장
        if all_notams:
            print(f"\n[저장] DynamoDB 저장 중...")
            for notam in all_notams:
                try:
                    self._save_to_dynamodb(notam)
                    saved_count += 1
                except Exception as e:
                    print(f"  ! 저장 오류: {notam.get('notam_id', 'Unknown')} - {e}")
                    error_count += 1

            print(f"  ✅ {saved_count}/{len(all_notams)}개 저장 완료")

            # S3 백업
            print(f"\n[백업] S3 백업 중...")
            try:
                self._backup_to_s3(all_notams)
                print(f"  ✅ S3 백업 완료")
            except Exception as e:
                print(f"  ❌ S3 백업 오류: {e}")

        print(f"\n{'='*60}")
        print(f"✅ 크롤링 완료!")
        print(f"{'='*60}\n")

        return {
            'status': 'SUCCESS',
            'total_found': len(all_notams),
            'saved': saved_count,
            'errors': error_count,
            'timestamp': datetime.now().isoformat()
        }

    def _fetch_notams(self, location: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """AIM 포털에서 NOTAM 가져오기"""

        notams = []

        for series in NOTAM_SERIES:
            data = {
                'selectLocation': location,
                'series': series,
                'startDate': start_time.strftime('%Y%m%d%H%M'),
                'endDate': end_time.strftime('%Y%m%d%H%M')
            }

            try:
                response = self.session.post(AIM_API_URL, data=data, timeout=10)
                response.raise_for_status()

                result = response.json()

                if isinstance(result, dict) and 'data' in result:
                    items = result['data']
                elif isinstance(result, list):
                    items = result
                else:
                    continue

                for item in items:
                    notam = self._parse_notam(item, location)
                    if notam:
                        notams.append(notam)

            except Exception as e:
                continue

        return notams

    def _parse_notam(self, raw_data: Dict, location: str) -> Optional[Dict]:
        """NOTAM 데이터 파싱"""

        try:
            notam_no = raw_data.get('notamNo', '')
            if not notam_no:
                return None

            # NOTAM ID 생성 (중복 방지)
            notam_id = f"{location}_{notam_no}"

            return {
                'notam_id': notam_id,
                'location': location,
                'notam_type': raw_data.get('series', ''),
                'status': 'ACTIVE',
                'issue_time': raw_data.get('issueTime', ''),
                'start_time': raw_data.get('startTime', ''),
                'end_time': raw_data.get('endTime', ''),
                'qcode': raw_data.get('qcode', ''),
                'full_text': raw_data.get('fullText', ''),
                'data_source': 'domestic',
                'crawl_timestamp': datetime.now().isoformat()
            }

        except Exception:
            return None

    def _save_to_dynamodb(self, notam: Dict):
        """DynamoDB에 저장"""

        # None 값 제거
        item = {k: v for k, v in notam.items() if v is not None and v != ''}

        self.table.put_item(Item=item)

    def _backup_to_s3(self, notams: List[Dict]):
        """S3에 백업"""

        now = datetime.now()
        key = f"backups/{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}-{now.minute:02d}.json"

        backup_data = {
            'timestamp': now.isoformat(),
            'count': len(notams),
            'notams': notams
        }

        self.s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(backup_data, ensure_ascii=False, indent=2),
            ContentType='application/json'
        )


def main():
    """메인 함수"""
    try:
        crawler = EC2NOTAMCrawler()
        result = crawler.crawl_domestic_notams(hours_back=2)

        # 결과 로깅
        with open('/home/ubuntu/crawler.log', 'a') as f:
            f.write(f"{datetime.now().isoformat()}: {json.dumps(result)}\n")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

        # 오류 로깅
        with open('/home/ubuntu/crawler_error.log', 'a') as f:
            f.write(f"{datetime.now().isoformat()}: {str(e)}\n")


if __name__ == '__main__':
    main()
