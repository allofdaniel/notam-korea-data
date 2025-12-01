"""
AWS Lambda NOTAM 크롤러 (개선 버전)
- 자동 오류 감지 및 알림
- 유연한 필드 매핑
- 다층 Fallback

작성일: 2025-11-11
"""

import json
import os
import boto3
from datetime import datetime, timezone
from decimal import Decimal
import requests
import pytz
from typing import Dict, List, Tuple

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))
sns_client = boto3.client('sns', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))

# 환경 변수
DYNAMODB_TABLE_NOTAMS = os.environ.get('DYNAMODB_TABLE_NOTAMS', 'NOTAM_Records')
DYNAMODB_TABLE_LOGS = os.environ.get('DYNAMODB_TABLE_LOGS', 'NOTAM_CrawlLogs')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')  # 알림용 SNS 토픽
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', '')

# DynamoDB 테이블
table_notams = dynamodb.Table(DYNAMODB_TABLE_NOTAMS)
table_logs = dynamodb.Table(DYNAMODB_TABLE_LOGS)


class NOTAMCrawlerMonitored:
    """
    개선된 NOTAM 크롤러
    - 자동 오류 감지
    - 유연한 필드 매핑
    - 알림 기능
    """

    # ============================================================
    # 필드 매핑 설정 (여러 가능한 필드명 시도)
    # ============================================================
    FIELD_MAPPINGS = {
        'notam_id': ['AIS_NUM', 'NOTAM_NUM', 'NOTAM_NO', 'NUM'],
        'location': ['LOCATION', 'LOC', 'AIRPORT_CODE'],
        'notam_type': ['AIS_TYPE', 'NOTAM_TYPE', 'TYPE'],
        'issue_time': ['ISSUE_TIME', 'ISSUED', 'ISSUE_DATE'],
        'start_time': ['START_TIME', 'FROM_TIME', 'VALID_FROM'],
        'end_time': ['END_TIME', 'TO_TIME', 'VALID_TO'],
        'qcode': ['QCODE', 'Q_CODE'],
        'full_text': ['ETEXTKO', 'ETEXT', 'TEXT_KO', 'DESCRIPTION']
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        })

        # 공항 코드
        self.domestic_airports = [
            'RKSI', 'RKSS', 'RKPK', 'RKPC', 'RKPS', 'RKPU',
            'RKSM', 'RKTH', 'RKPD', 'RKTL', 'RKNW', 'RKJK',
            'RKJB', 'RKJY', 'RKJJ', 'RKTN', 'RKTU', 'RKNY'
        ]

        # API URL (여러 후보)
        self.api_urls = [
            "https://aim.koca.go.kr/apisvc/getIBSheetData.do",
            # 백업 URL이 있다면 여기 추가
        ]

        self.consecutive_failures = 0
        self.structure_changed = False

    def get_field_value(self, record: Dict, field_name: str) -> str:
        """
        유연한 필드 매핑 - 여러 필드명 시도

        구조가 변경되어도 가능한 필드명을 모두 시도
        """
        possible_fields = self.FIELD_MAPPINGS.get(field_name, [field_name])

        for field in possible_fields:
            value = record.get(field)
            if value:
                # 새로운 필드명 발견 시 로깅
                if field != possible_fields[0]:
                    print(f"[WARN] 필드명 변경 감지: {field_name} → {field}")
                    self.structure_changed = True
                return value

        # 모든 시도 실패
        print(f"[ERROR] 필드 '{field_name}' 를 찾을 수 없음: 시도한 필드 {possible_fields}")
        return ''

    def fetch_notam_data(self, data_source: str, hours_back: int) -> Tuple[List[Dict], str]:
        """NOTAM 데이터 가져오기 (여러 URL 시도)"""

        # 여러 API URL 시도
        for api_url in self.api_urls:
            try:
                payload = self.get_search_payload(data_source, hours_back)

                response = self.session.post(api_url, data=payload, timeout=30)
                response.raise_for_status()

                # JSON 파싱
                data = response.json()

                if not data or 'data' not in data:
                    # 응답 구조 변경 가능성
                    print(f"[WARN] 응답 구조 변경 가능성: {list(data.keys())}")

                    # 다른 가능한 키 시도
                    for key in ['records', 'items', 'result', 'notams']:
                        if key in data:
                            print(f"[INFO] 대체 키 발견: '{key}'")
                            data['data'] = data[key]
                            self.structure_changed = True
                            break
                    else:
                        continue  # 다음 URL 시도

                records = data['data']
                print(f"[INFO] {data_source}: {len(records)}개 발견 (URL: {api_url})")

                # 필드 매핑 (유연하게)
                notam_list = []
                for record in records:
                    notam = {
                        'notam_id': self.get_field_value(record, 'notam_id'),
                        'location': self.get_field_value(record, 'location'),
                        'notam_type': self.get_field_value(record, 'notam_type'),
                        'issue_time': self.get_field_value(record, 'issue_time'),
                        'start_time': self.get_field_value(record, 'start_time'),
                        'end_time': self.get_field_value(record, 'end_time'),
                        'qcode': self.get_field_value(record, 'qcode'),
                        'full_text': self.get_field_value(record, 'full_text'),
                        'full_text_detail': json.dumps(record, ensure_ascii=False),
                        'data_source': data_source,
                        'crawl_timestamp': datetime.now(timezone.utc).isoformat()
                    }

                    # 필수 필드 검증
                    if notam['notam_id'] and notam['location']:
                        notam_list.append(notam)
                    else:
                        print(f"[WARN] 필수 필드 누락: {record}")

                # 성공
                self.consecutive_failures = 0
                return notam_list, None

            except Exception as e:
                print(f"[ERROR] API 요청 실패 ({api_url}): {e}")
                continue

        # 모든 URL 실패
        error_msg = f"모든 API URL 실패 (시도: {len(self.api_urls)}개)"
        self.consecutive_failures += 1
        return [], error_msg

    def send_alert(self, subject: str, message: str):
        """SNS 알림 발송"""
        if not SNS_TOPIC_ARN:
            print("[WARN] SNS 토픽 미설정, 알림 생략")
            return

        try:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"[NOTAM 크롤러] {subject}",
                Message=message
            )
            print(f"[INFO] 알림 발송: {subject}")
        except Exception as e:
            print(f"[ERROR] 알림 발송 실패: {e}")

    def check_and_alert(self):
        """오류 체크 및 알림"""

        # 연속 실패 체크
        if self.consecutive_failures >= 3:
            self.send_alert(
                "크롤링 연속 실패",
                f"NOTAM 크롤러가 {self.consecutive_failures}회 연속 실패했습니다.\n\n"
                f"가능한 원인:\n"
                f"1. API URL 변경\n"
                f"2. API 페이로드 구조 변경\n"
                f"3. 네트워크 문제\n\n"
                f"조치: lambda_crawler.py 코드 확인 필요"
            )

        # 구조 변경 감지
        if self.structure_changed:
            self.send_alert(
                "API 구조 변경 감지",
                f"NOTAM API의 응답 구조 변경이 감지되었습니다.\n\n"
                f"현재는 자동으로 대응했지만, 코드 검토를 권장합니다.\n\n"
                f"확인 위치: lambda_crawler.py FIELD_MAPPINGS"
            )

    def get_search_payload(self, data_source: str, hours_back: int) -> Dict:
        """검색 페이로드 생성"""
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        now_utc = now.astimezone(timezone.utc)
        from_time = now_utc.replace(hour=now_utc.hour - hours_back, minute=0, second=0, microsecond=0)

        from_hhmm = from_time.strftime("%H%M")
        to_hhmm = now_utc.strftime("%H%M")
        from_date = from_time.strftime("%Y%m%d")
        to_date = now_utc.strftime("%Y%m%d")

        is_international = (data_source == 'international')
        inorout = 'Y' if is_international else 'N'
        location_str = "" if is_international else ",".join(self.domestic_airports)
        series_str = "A,C,D,E,G,Z,SNOWTAM"

        payload = {
            'inorout': inorout,
            'startdate': from_date,
            'enddate': to_date,
            'starttime': from_hhmm,
            'endtime': to_hhmm,
            'location': location_str,
            'series': series_str,
            'qcode': '',
            'Contents': '',
            'Num': '',
            'newE': '',
            'sheetId': 'sheetNotam',
            'ibsheetName': 'notamList',
            'ibsheetVersion': '8'
        }

        return payload

    def save_to_dynamodb(self, notam_list: List[Dict], data_source: str) -> int:
        """DynamoDB에 저장"""
        saved_count = 0

        for notam in notam_list:
            try:
                item = {
                    'notam_id': notam['notam_id'],
                    'location': notam['location'],
                    'notam_type': notam['notam_type'],
                    'issue_time': notam['issue_time'],
                    'start_time': notam['start_time'],
                    'end_time': notam['end_time'],
                    'qcode': notam['qcode'],
                    'full_text': notam['full_text'],
                    'full_text_detail': notam['full_text_detail'],
                    'data_source': data_source,
                    'crawl_timestamp': notam['crawl_timestamp'],
                    'ttl': int(datetime.now().timestamp()) + 30*24*3600
                }

                table_notams.put_item(Item=item)
                saved_count += 1

            except Exception as e:
                print(f"[ERROR] DynamoDB 저장 실패: {e}")

        return saved_count

    def crawl_notam(self, data_source: str, hours_back: int = 24) -> Dict:
        """NOTAM 크롤링 실행"""
        start_time = datetime.now()

        print(f"\n[START] {data_source.upper()} NOTAM 크롤링")

        # 데이터 가져오기
        notam_list, error = self.fetch_notam_data(data_source, hours_back)

        if error:
            execution_time = (datetime.now() - start_time).total_seconds()

            # 알림 체크
            self.check_and_alert()

            return {
                'status': 'FAILED',
                'records_found': 0,
                'records_saved': 0,
                'execution_time': execution_time,
                'error': error
            }

        # DynamoDB 저장
        saved_count = self.save_to_dynamodb(notam_list, data_source)

        execution_time = (datetime.now() - start_time).total_seconds()

        # 알림 체크 (구조 변경 감지)
        self.check_and_alert()

        print(f"[SUCCESS] {data_source}: {len(notam_list)}개 발견, {saved_count}개 저장")

        return {
            'status': 'SUCCESS',
            'records_found': len(notam_list),
            'records_saved': saved_count,
            'execution_time': execution_time,
            'structure_changed': self.structure_changed
        }


def lambda_handler(event, context):
    """Lambda 핸들러"""
    print("[INFO] Lambda 크롤러 시작 (모니터링 버전)")

    crawler = NOTAMCrawlerMonitored()

    # 국내 + 국제 크롤링
    domestic_result = crawler.crawl_notam('domestic', hours_back=24)
    international_result = crawler.crawl_notam('international', hours_back=24)

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'success',
            'domestic': domestic_result,
            'international': international_result
        })
    }

    return response
