"""
자동 NOTAM 크롤러 → DynamoDB 업로드
Windows Task Scheduler로 5분마다 실행

작성일: 2025-11-13
"""

import sqlite3
import boto3
import requests
import pytz
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List

# AWS 설정
AWS_REGION = 'ap-southeast-2'
DYNAMODB_TABLE_NAME = 'NOTAM_Records'

# DynamoDB 클라이언트
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


class NOTAMAutoCrawler:
    """자동 NOTAM 크롤러"""

    def __init__(self):
        self.base_url = 'https://aim.koca.go.kr'
        self.search_endpoint = f'{self.base_url}/xNotam/searchAllNotam.do'

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/xNotam/?language=ko_KR',
            'Connection': 'keep-alive'
        })

        # 국내 18개 공항
        self.domestic_airports = [
            'RKSI', 'RKSS', 'RKPK', 'RKPC', 'RKPS', 'RKPU',
            'RKSM', 'RKTH', 'RKPD', 'RKTL', 'RKNW', 'RKJK',
            'RKJB', 'RKJY', 'RKJJ', 'RKTN', 'RKTU', 'RKNY'
        ]

        self.series_types = ['A', 'C', 'D', 'E', 'G', 'Z', 'SNOWTAM']

    def get_search_payload(self, hours_back: int = 24) -> Dict:
        """검색 페이로드 생성 (국내 전용)"""
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        now_utc = now.astimezone(timezone.utc)
        from_time = now_utc - timedelta(hours=hours_back)

        payload = {
            'inorout': 'N',  # 국내 전용
            'startdate': from_time.strftime("%Y%m%d"),
            'enddate': now_utc.strftime("%Y%m%d"),
            'starttime': from_time.strftime("%H%M"),
            'endtime': now_utc.strftime("%H%M"),
            'location': ",".join(self.domestic_airports),
            'series': ",".join(self.series_types),
            'qcode': '',
            'Contents': '',
            'Num': '',
            'newE': '',
            'sheetId': 'sheetNotam',
            'ibsheetName': 'notamList',
            'ibsheetVersion': '8'
        }

        return payload

    def fetch_notam_data(self, hours_back: int = 24) -> List[Dict]:
        """NOTAM 데이터 가져오기"""
        payload = self.get_search_payload(hours_back)

        try:
            response = self.session.post(self.api_url, data=payload, timeout=30)
            response.raise_for_status()

            data = response.json()

            if not data or 'data' not in data:
                print("[WARN] 빈 응답")
                return []

            records = data['data']
            print(f"[INFO] {len(records)}개 NOTAM 발견")

            # 필드 매핑
            notam_list = []
            for record in records:
                notam = {
                    'notam_id': record.get('AIS_NUM', ''),
                    'location': record.get('LOCATION', ''),
                    'notam_type': record.get('AIS_TYPE', ''),
                    'status': 'ACTIVE',  # 기본값
                    'issue_time': record.get('ISSUE_TIME', ''),
                    'start_time': record.get('START_TIME', ''),
                    'end_time': record.get('END_TIME', ''),
                    'qcode': record.get('QCODE', ''),
                    'full_text': record.get('ETEXTKO', ''),
                    'data_source': 'domestic',
                    'crawl_timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                }

                # None 값 제거
                notam = {k: v for k, v in notam.items() if v is not None and v != ''}

                notam_list.append(notam)

            return notam_list

        except Exception as e:
            print(f"[ERROR] API 오류: {e}")
            return []

    def save_to_dynamodb(self, notam_list: List[Dict]) -> int:
        """DynamoDB에 저장"""
        saved_count = 0

        for notam in notam_list:
            try:
                # DynamoDB에 저장
                table.put_item(Item=notam)
                saved_count += 1

            except Exception as e:
                print(f"[ERROR] 저장 실패 ({notam['notam_id']}): {e}")

        print(f"[INFO] DynamoDB 저장: {saved_count}/{len(notam_list)}개")
        return saved_count

    def run(self):
        """크롤링 실행"""
        print("=" * 60)
        print("자동 NOTAM 크롤러 시작")
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 1. 데이터 가져오기
        notam_list = self.fetch_notam_data(hours_back=24)

        if not notam_list:
            print("[WARN] 수집된 데이터 없음")
            return

        # 2. DynamoDB 저장
        saved_count = self.save_to_dynamodb(notam_list)

        print()
        print("=" * 60)
        print(f"✅ 완료: {saved_count}개 저장")
        print("=" * 60)

        # 3. 로그 파일 저장
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'records_found': len(notam_list),
            'records_saved': saved_count
        }

        with open('crawler_log.json', 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    try:
        crawler = NOTAMAutoCrawler()
        crawler.run()

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

        # 오류 로그
        with open('crawler_error.log', 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()}: {e}\n")
