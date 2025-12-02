"""
AWS Lambda NOTAM API
S3에서 154,986개 전체 NOTAM 제공 (서버리스)
"""
import boto3
import json
from datetime import datetime
from urllib.parse import parse_qs

s3 = boto3.client('s3')
BUCKET_NAME = 'notam-korea-data'
COMPLETE_DATA_KEY = 'notam_complete/20251201_100751/notam_final_complete.json'

# Lambda 컨테이너 재사용을 위한 글로벌 캐시
ALL_NOTAMS = None

def load_all_notams():
    """S3에서 전체 NOTAM 로드 (Lambda 컨테이너 재사용 시 캐시 활용)"""
    global ALL_NOTAMS
    if ALL_NOTAMS is not None:
        print(f"[CACHE] 캐시된 NOTAM 사용: {len(ALL_NOTAMS)}개")
        return ALL_NOTAMS

    print(f"[LOAD] S3에서 전체 NOTAM 로드 중: {COMPLETE_DATA_KEY}")
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=COMPLETE_DATA_KEY)
    ALL_NOTAMS = json.loads(obj['Body'].read().decode('utf-8'))
    print(f"[OK] {len(ALL_NOTAMS)}개 NOTAM 로드 완료")
    return ALL_NOTAMS

def parse_notam_date(date_str):
    """NOTAM 날짜 파싱 (YYMMDDHHMM 형식)"""
    if not date_str or len(date_str) < 8:
        return None
    try:
        year = int('20' + date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        hour = int(date_str[6:8]) if len(date_str) >= 8 else 0
        minute = int(date_str[8:10]) if len(date_str) >= 10 else 0
        return datetime(year, month, day, hour, minute)
    except:
        return None

def get_notam_status(notam, current_time=None):
    """NOTAM 상태 분류"""
    if current_time is None:
        current_time = datetime.now()

    effective_start = parse_notam_date(notam.get('effective_start', ''))
    effective_end = parse_notam_date(notam.get('effective_end', ''))

    # 트리거 NOTAM 체크
    e_text = notam.get('e_text', '').upper()
    trigger_keywords = ['TRIGGER', 'NOTAM TO FOLLOW', 'NEW NOTAM', 'WILL TAKE PLACE']
    is_trigger = any(keyword in e_text for keyword in trigger_keywords)

    if is_trigger:
        return 'trigger'

    if not effective_end:
        if effective_start and effective_start > current_time:
            return 'scheduled'
        return 'active'

    if effective_start and effective_start > current_time:
        return 'scheduled'

    if effective_end < current_time:
        return 'expired'

    return 'active'

def categorize_notams(notams, filter_date=None):
    """NOTAM 분류 및 통계"""
    current_time = datetime.now()

    # 날짜 필터링: 해당 날짜에 활성이었던 NOTAM
    if filter_date:
        try:
            filter_dt = datetime.strptime(filter_date, '%Y-%m-%d')
            filter_dt = filter_dt.replace(hour=12, minute=0)

            filtered = []
            for n in notams:
                start = parse_notam_date(n.get('effective_start', ''))
                end = parse_notam_date(n.get('effective_end', ''))

                if start and start <= filter_dt:
                    if not end or end >= filter_dt:
                        filtered.append(n)

            notams = filtered
            current_time = filter_dt
        except Exception as e:
            print(f"[WARN] 날짜 필터링 오류: {e}")

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

def get_query_param(event, param_name, default=None):
    """쿼리 파라미터 추출"""
    params = event.get('queryStringParameters') or {}
    return params.get(param_name, default)

def lambda_response(status_code, body):
    """Lambda 응답 형식"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body, ensure_ascii=False)
    }

def lambda_handler(event, context):
    """Lambda 핸들러 (API Gateway 이벤트)"""

    print(f"[EVENT] {json.dumps(event)}")

    # OPTIONS 요청 (CORS preflight)
    if event.get('httpMethod') == 'OPTIONS':
        return lambda_response(200, {'message': 'OK'})

    # 경로 추출
    path = event.get('path', '').rstrip('/')

    try:
        all_notams = load_all_notams()

        # 라우팅
        if path == '/notams/stats':
            filter_date = get_query_param(event, 'date')
            _, stats = categorize_notams(all_notams, filter_date)
            return lambda_response(200, stats)

        elif path == '/notams/active':
            filter_date = get_query_param(event, 'date')
            categorized, stats = categorize_notams(all_notams, filter_date)
            return lambda_response(200, {
                'stats': stats,
                'data': categorized['active']
            })

        elif path == '/notams/realtime':
            filter_date = get_query_param(event, 'date')
            limit = int(get_query_param(event, 'limit', 10000))

            categorized, stats = categorize_notams(all_notams, filter_date)
            active_notams = categorized['active'][:limit]

            return lambda_response(200, {
                'count': len(categorized['active']),
                'data': active_notams,
                'returned': len(active_notams)
            })

        elif path == '/notams/expired':
            filter_date = get_query_param(event, 'date')
            categorized, stats = categorize_notams(all_notams, filter_date)
            return lambda_response(200, {
                'stats': stats,
                'data': categorized['expired']
            })

        elif path == '/notams/trigger':
            filter_date = get_query_param(event, 'date')
            categorized, stats = categorize_notams(all_notams, filter_date)
            return lambda_response(200, {
                'stats': stats,
                'data': categorized['trigger']
            })

        elif path == '/notams/complete':
            filter_date = get_query_param(event, 'date')
            limit = int(get_query_param(event, 'limit', 1000))

            categorized, stats = categorize_notams(all_notams, filter_date)

            result = {
                'stats': stats,
                'categorized': {
                    'active': categorized['active'][:limit],
                    'expired': categorized['expired'][:limit],
                    'trigger': categorized['trigger'][:limit],
                    'scheduled': categorized['scheduled'][:limit]
                }
            }
            return lambda_response(200, result)

        elif path.startswith('/notams/date/'):
            date = path.split('/')[-1]
            categorized, stats = categorize_notams(all_notams, date)
            return lambda_response(200, {
                'stats': stats,
                'categorized': categorized
            })

        elif path == '/health':
            return lambda_response(200, {
                'status': 'ok',
                'total_notams': len(all_notams),
                'server_time': datetime.now().isoformat(),
                'lambda': True
            })

        else:
            return lambda_response(404, {
                'error': 'Not Found',
                'path': path,
                'available_endpoints': [
                    '/notams/stats',
                    '/notams/active',
                    '/notams/realtime',
                    '/notams/expired',
                    '/notams/trigger',
                    '/notams/complete',
                    '/notams/date/<date>',
                    '/health'
                ]
            })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return lambda_response(500, {
            'error': 'Internal Server Error',
            'message': str(e)
        })
