"""
Lambda 함수: 완전한 NOTAM 조회 API
- S3에서 154,986개 전체 NOTAM 조회
- 날짜별 필터링
- 상태별 분류 (활성/만료/트리거)
"""
import json
import boto3
from datetime import datetime, timedelta
from dateutil import parser

s3 = boto3.client('s3')
BUCKET_NAME = 'notam-korea-data'
COMPLETE_DATA_KEY = 'notam_complete/20251201_100751/notam_final_complete.json'

def parse_notam_date(date_str):
    """NOTAM 날짜 파싱 (YYMMDDHHMM 형식)"""
    if not date_str or len(date_str) < 8:
        return None
    try:
        # YYMMDDHHMM -> YYYY-MM-DD HH:MM
        year = int('20' + date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        hour = int(date_str[6:8]) if len(date_str) >= 8 else 0
        minute = int(date_str[8:10]) if len(date_str) >= 10 else 0
        return datetime(year, month, day, hour, minute)
    except:
        return None

def get_notam_status(notam, current_time=None):
    """
    NOTAM 상태 분류
    Returns: 'active', 'expired', 'trigger', 'scheduled'
    """
    if current_time is None:
        current_time = datetime.now()

    effective_start = parse_notam_date(notam.get('effective_start', ''))
    effective_end = parse_notam_date(notam.get('effective_end', ''))

    # 트리거 NOTAM 체크 (effective_end가 없고 특정 키워드 포함)
    e_text = notam.get('e_text', '').upper()
    trigger_keywords = ['TRIGGER', 'NOTAM TO FOLLOW', 'NEW NOTAM', 'WILL TAKE PLACE']
    is_trigger = any(keyword in e_text for keyword in trigger_keywords)

    if is_trigger:
        return 'trigger'

    # effective_end가 없는 경우 (영구 또는 추후 발표)
    if not effective_end:
        if effective_start and effective_start > current_time:
            return 'scheduled'  # 미래 시작
        return 'active'  # 종료일 미정 (계속 유효)

    # 날짜 기반 상태 확인
    if effective_start and effective_start > current_time:
        return 'scheduled'  # 아직 시작 안 함

    if effective_end < current_time:
        return 'expired'  # 만료됨

    return 'active'  # 현재 활성

def categorize_notams(notams, filter_date=None):
    """NOTAM 분류 및 통계"""
    current_time = datetime.now()

    # 날짜 필터링
    if filter_date:
        try:
            filter_dt = datetime.strptime(filter_date, '%Y-%m-%d')
            notams = [n for n in notams if n.get('crawl_date', '').startswith(filter_date)]
        except:
            pass  # 날짜 형식 오류 시 필터링 안 함

    categorized = {
        'active': [],
        'expired': [],
        'trigger': [],
        'scheduled': []
    }

    for notam in notams:
        status = get_notam_status(notam, current_time)
        categorized[status].append({
            **notam,
            'status': status
        })

    stats = {
        'total': len(notams),
        'active': len(categorized['active']),
        'expired': len(categorized['expired']),
        'trigger': len(categorized['trigger']),
        'scheduled': len(categorized['scheduled']),
        'filter_date': filter_date,
        'current_time': current_time.isoformat()
    }

    return categorized, stats

def lambda_handler(event, context):
    """Lambda 핸들러"""
    print(f"Event: {json.dumps(event)}")

    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }

    path = event.get('path', '')
    resource = event.get('resource', '')
    query_params = event.get('queryStringParameters') or {}

    try:
        # S3에서 전체 데이터 로드
        print(f"Loading complete data from S3: {COMPLETE_DATA_KEY}")
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=COMPLETE_DATA_KEY)
        all_notams = json.loads(obj['Body'].read().decode('utf-8'))
        print(f"Loaded {len(all_notams)} NOTAMs from S3")

        # 엔드포인트 라우팅

        # 1. 통계만 반환
        if '/stats' in path or '/stats' in resource:
            filter_date = query_params.get('date')
            _, stats = categorize_notams(all_notams, filter_date)

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(stats, ensure_ascii=False)
            }

        # 2. 활성 NOTAM만
        elif '/active' in path or '/active' in resource:
            filter_date = query_params.get('date')
            categorized, stats = categorize_notams(all_notams, filter_date)

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'stats': stats,
                    'data': categorized['active']
                }, ensure_ascii=False)
            }

        # 3. 만료 NOTAM만
        elif '/expired' in path or '/expired' in resource:
            filter_date = query_params.get('date')
            categorized, stats = categorize_notams(all_notams, filter_date)

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'stats': stats,
                    'data': categorized['expired']
                }, ensure_ascii=False)
            }

        # 4. 트리거 NOTAM만
        elif '/trigger' in path or '/trigger' in resource:
            filter_date = query_params.get('date')
            categorized, stats = categorize_notams(all_notams, filter_date)

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'stats': stats,
                    'data': categorized['trigger']
                }, ensure_ascii=False)
            }

        # 5. 전체 (분류된 상태로)
        elif '/complete' in path or '/complete' in resource:
            filter_date = query_params.get('date')
            categorized, stats = categorize_notams(all_notams, filter_date)

            # limit 파라미터 지원
            limit = int(query_params.get('limit', 1000))

            result = {
                'stats': stats,
                'categorized': {
                    'active': categorized['active'][:limit],
                    'expired': categorized['expired'][:limit],
                    'trigger': categorized['trigger'][:limit],
                    'scheduled': categorized['scheduled'][:limit]
                }
            }

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result, ensure_ascii=False)
            }

        # 6. 날짜별 조회
        elif '/date/' in path or '/date/' in resource:
            date_str = path.split('/date/')[-1] if '/date/' in path else resource.split('/date/')[-1]
            date_str = date_str.strip('{}')  # API Gateway path variable

            categorized, stats = categorize_notams(all_notams, date_str)

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'stats': stats,
                    'categorized': categorized
                }, ensure_ascii=False)
            }

        # 기본: API 정보
        else:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'name': 'NOTAM Complete API',
                    'total_notams': len(all_notams),
                    'endpoints': {
                        '/notams/stats': '통계 (전체/활성/만료/트리거)',
                        '/notams/stats?date=2024-12-01': '특정 날짜 통계',
                        '/notams/active': '현재 활성 NOTAM',
                        '/notams/expired': '만료된 NOTAM',
                        '/notams/trigger': '트리거 NOTAM',
                        '/notams/complete': '전체 NOTAM (분류됨)',
                        '/notams/complete?limit=100': '전체 NOTAM (100개 제한)',
                        '/notams/date/2024-12-01': '특정 날짜 NOTAM'
                    }
                }, ensure_ascii=False)
            }

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            }, ensure_ascii=False)
        }

# 로컬 테스트
if __name__ == '__main__':
    # 테스트 이벤트
    test_event = {
        'path': '/notams/stats',
        'resource': '/notams/stats',
        'queryStringParameters': {'date': '2024-12-01'}
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2, ensure_ascii=False))
