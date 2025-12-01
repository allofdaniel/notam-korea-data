"""
AWS Lambda NOTAM 크롤러
- DynamoDB에 데이터 저장
- S3에 백업
- EventBridge로 1분마다 자동 실행

작성일: 2025-11-11
"""

import json
import os
import boto3
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import requests
import pytz
from typing import Dict, List, Tuple

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))

# 환경 변수
DYNAMODB_TABLE_NOTAMS = os.environ.get('DYNAMODB_TABLE_NOTAMS', 'NOTAM_Records')
DYNAMODB_TABLE_LOGS = os.environ.get('DYNAMODB_TABLE_LOGS', 'NOTAM_CrawlLogs')
DYNAMODB_TABLE_CHANGES = os.environ.get('DYNAMODB_TABLE_CHANGES', 'NOTAM_Changes')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', '')

# DynamoDB 테이블
table_notams = dynamodb.Table(DYNAMODB_TABLE_NOTAMS)
table_logs = dynamodb.Table(DYNAMODB_TABLE_LOGS)
table_changes = dynamodb.Table(DYNAMODB_TABLE_CHANGES)


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal을 JSON으로 변환"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class NOTAMCrawlerLambda:
    """AWS Lambda용 NOTAM 크롤러"""

    def __init__(self):
        self.session = requests.Session()
        # AIM 포털 접근을 위한 상세 헤더 (Lambda에서 작동하도록 개선)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'https://aim.koca.go.kr/aip/index.do',
            'Origin': 'https://aim.koca.go.kr',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive'
        })

        # 공항 코드 (18개)
        self.domestic_airports = [
            'RKSI', 'RKSS', 'RKPK', 'RKPC', 'RKPS', 'RKPU',
            'RKSM', 'RKTH', 'RKPD', 'RKTL', 'RKNW', 'RKJK',
            'RKJB', 'RKJY', 'RKJJ', 'RKTN', 'RKTU', 'RKNY'
        ]

        # SERIES 타입
        self.series_types = ['A', 'C', 'D', 'E', 'G', 'Z', 'SNOWTAM']

        # AIM 포털 API URL
        self.api_url = "https://aim.koca.go.kr/apisvc/getIBSheetData.do"

    def get_search_payload(self, data_source: str, hours_back: int = 24) -> Dict:
        """검색 페이로드 생성"""
        # UTC 시간 계산
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        now_utc = now.astimezone(timezone.utc)
        from_time = now_utc - timedelta(hours=hours_back)

        # HHMM 형식
        from_hhmm = from_time.strftime("%H%M")
        to_hhmm = now_utc.strftime("%H%M")

        # 날짜 형식
        from_date = from_time.strftime("%Y%m%d")
        to_date = now_utc.strftime("%Y%m%d")

        # 국내/국제 구분
        is_international = (data_source == 'international')
        inorout = 'Y' if is_international else 'N'

        # 공항 코드 문자열
        if is_international:
            location_str = ""
        else:
            location_str = ",".join(self.domestic_airports)

        # SERIES 문자열
        series_str = ",".join(self.series_types)

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

    def fetch_notam_data(self, data_source: str, hours_back: int) -> Tuple[List[Dict], str]:
        """NOTAM 데이터 가져오기"""
        payload = self.get_search_payload(data_source, hours_back)

        try:
            response = self.session.post(self.api_url, data=payload, timeout=30)
            response.raise_for_status()

            # JSON 파싱
            data = response.json()

            if not data or 'data' not in data:
                return [], "Empty response"

            records = data['data']
            print(f"[INFO] {data_source}: {len(records)}개 발견")

            # 필드 매핑
            notam_list = []
            for record in records:
                notam = {
                    'notam_id': record.get('AIS_NUM', ''),
                    'location': record.get('LOCATION', ''),
                    'notam_type': record.get('AIS_TYPE', ''),
                    'issue_time': record.get('ISSUE_TIME', ''),
                    'start_time': record.get('START_TIME', ''),
                    'end_time': record.get('END_TIME', ''),
                    'qcode': record.get('QCODE', ''),
                    'full_text': record.get('ETEXTKO', ''),
                    'full_text_detail': json.dumps(record, ensure_ascii=False),
                    'data_source': data_source,
                    'crawl_timestamp': datetime.now(timezone.utc).isoformat()
                }
                notam_list.append(notam)

            return notam_list, None

        except Exception as e:
            error_msg = f"API 오류: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return [], error_msg

    def save_to_dynamodb(self, notam_list: List[Dict], data_source: str) -> int:
        """DynamoDB에 저장"""
        saved_count = 0

        for notam in notam_list:
            try:
                # DynamoDB는 float를 지원하지 않으므로 Decimal 변환
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
                    'ttl': int(datetime.now().timestamp()) + 30*24*3600  # 30일 TTL
                }

                # PUT (덮어쓰기)
                table_notams.put_item(Item=item)
                saved_count += 1

            except Exception as e:
                print(f"[ERROR] DynamoDB 저장 실패: {notam['notam_id']} - {e}")

        print(f"[INFO] DynamoDB 저장: {saved_count}/{len(notam_list)}개")
        return saved_count

    def save_to_s3(self, notam_list: List[Dict], data_source: str) -> bool:
        """S3에 백업"""
        if not S3_BUCKET_NAME:
            print("[WARN] S3 버킷 미설정, 백업 생략")
            return False

        try:
            # 날짜별 폴더
            now = datetime.now(pytz.timezone('Asia/Seoul'))
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H%M%S")

            # S3 키
            s3_key = f"daily/{date_str}/{data_source}_{time_str}.json"

            # JSON 변환
            json_data = json.dumps(notam_list, ensure_ascii=False, indent=2, cls=DecimalEncoder)

            # S3 업로드
            s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json'
            )

            print(f"[INFO] S3 백업: s3://{S3_BUCKET_NAME}/{s3_key}")
            return True

        except Exception as e:
            print(f"[ERROR] S3 백업 실패: {e}")
            return False

    def save_crawl_log(self, data_source: str, status: str, records_found: int,
                      records_saved: int, execution_time: float, error: str = None):
        """크롤링 로그 저장"""
        try:
            log_id = f"{data_source}_{int(datetime.now().timestamp() * 1000)}"
            timestamp = int(datetime.now().timestamp())

            item = {
                'log_id': log_id,
                'timestamp': timestamp,
                'data_source': data_source,
                'status': status,
                'records_found': records_found,
                'records_saved': records_saved,
                'execution_time': Decimal(str(round(execution_time, 3))),
                'error_message': error or '',
                'crawl_time': datetime.now(timezone.utc).isoformat()
            }

            table_logs.put_item(Item=item)
            print(f"[INFO] 크롤링 로그 저장: {log_id}")

        except Exception as e:
            print(f"[ERROR] 로그 저장 실패: {e}")

    def crawl_notam(self, data_source: str, hours_back: int = 24) -> Dict:
        """NOTAM 크롤링 실행"""
        start_time = datetime.now()

        print(f"\n[START] {data_source.upper()} NOTAM 크롤링")

        # 데이터 가져오기
        notam_list, error = self.fetch_notam_data(data_source, hours_back)

        if error:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.save_crawl_log(data_source, 'FAILED', 0, 0, execution_time, error)
            return {
                'status': 'FAILED',
                'records_found': 0,
                'records_saved': 0,
                'execution_time': execution_time,
                'error': error
            }

        # DynamoDB 저장
        saved_count = self.save_to_dynamodb(notam_list, data_source)

        # S3 백업
        self.save_to_s3(notam_list, data_source)

        execution_time = (datetime.now() - start_time).total_seconds()

        # 로그 저장
        self.save_crawl_log(data_source, 'SUCCESS', len(notam_list), saved_count, execution_time)

        print(f"[SUCCESS] {data_source}: {len(notam_list)}개 발견, {saved_count}개 저장")

        return {
            'status': 'SUCCESS',
            'records_found': len(notam_list),
            'records_saved': saved_count,
            'execution_time': execution_time
        }


def lambda_handler(event, context):
    """
    AWS Lambda 핸들러 함수
    EventBridge에서 1분마다 호출됨
    """
    print("[INFO] Lambda 크롤러 시작")
    print(f"[INFO] 이벤트: {json.dumps(event)}")

    crawler = NOTAMCrawlerLambda()

    # 국내 NOTAM 크롤링 (비용 절감: 국내만 수집)
    domestic_result = crawler.crawl_notam('domestic', hours_back=24)

    # 국제 NOTAM 크롤링 비활성화 (비용 절감)
    # international_result = crawler.crawl_notam('international', hours_back=24)
    international_result = {
        'status': 'SKIPPED',
        'records_found': 0,
        'records_saved': 0,
        'execution_time': 0,
        'message': '비용 절감을 위해 국내 NOTAM만 수집'
    }

    # 결과 반환
    response = {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'status': 'success',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'domestic': domestic_result,
            'international': international_result,
            'total_found': domestic_result['records_found'],
            'total_saved': domestic_result['records_saved']
        }, cls=DecimalEncoder)
    }

    print(f"[INFO] Lambda 크롤러 완료")
    print(f"[INFO] 국내: {domestic_result['records_found']}개")
    print(f"[INFO] 국제: {international_result['records_found']}개")

    return response


# 로컬 테스트용
if __name__ == '__main__':
    # 로컬에서 테스트 시 환경 변수 설정
    os.environ['DYNAMODB_TABLE_NOTAMS'] = 'NOTAM_Records'
    os.environ['DYNAMODB_TABLE_LOGS'] = 'NOTAM_CrawlLogs'
    os.environ['DYNAMODB_TABLE_CHANGES'] = 'NOTAM_Changes'
    os.environ['S3_BUCKET_NAME'] = 'notam-backup-test'
    os.environ['AWS_REGION'] = 'ap-northeast-2'

    # 테스트 실행
    result = lambda_handler({}, {})
    print(json.dumps(json.loads(result['body']), indent=2, cls=DecimalEncoder))
