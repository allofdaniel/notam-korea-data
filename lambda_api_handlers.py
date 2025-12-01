"""
AWS Lambda API 핸들러
API Gateway와 연동되어 REST API 제공

엔드포인트:
- GET /api/notams - NOTAM 목록 조회
- GET /api/notams/{id} - 특정 NOTAM 조회
- GET /api/stats - 통계 조회
- POST /api/crawl - 수동 크롤링 트리거

작성일: 2025-11-11
"""

import json
import os
import boto3
from datetime import datetime, timezone
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# AWS 클라이언트
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))
lambda_client = boto3.client('lambda', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))

# 환경 변수
DYNAMODB_TABLE_NOTAMS = os.environ.get('DYNAMODB_TABLE_NOTAMS', 'NOTAM_Records')
DYNAMODB_TABLE_LOGS = os.environ.get('DYNAMODB_TABLE_LOGS', 'NOTAM_CrawlLogs')
DYNAMODB_TABLE_CHANGES = os.environ.get('DYNAMODB_TABLE_CHANGES', 'NOTAM_Changes')
CRAWLER_LAMBDA_NAME = os.environ.get('CRAWLER_LAMBDA_NAME', 'notam-crawler')

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


def create_response(status_code: int, body: dict) -> dict:
    """API Gateway 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(body, ensure_ascii=False, cls=DecimalEncoder)
    }


# ============================================================
# 1. GET /api/notams - NOTAM 목록 조회
# ============================================================

def get_notams_list(event, context):
    """
    NOTAM 목록 조회

    쿼리 파라미터:
    - data_source: domestic/international (기본: domestic)
    - location: 공항 코드 (선택)
    - limit: 최대 개수 (기본: 100, 최대: 1000)
    - last_key: 페이지네이션용 (선택)
    """
    try:
        # 쿼리 파라미터 파싱
        params = event.get('queryStringParameters') or {}
        data_source = params.get('data_source', 'domestic')
        location = params.get('location')
        limit = min(int(params.get('limit', 100)), 1000)
        last_key = params.get('last_key')

        print(f"[INFO] NOTAM 목록 조회: data_source={data_source}, location={location}, limit={limit}")

        # DynamoDB 쿼리
        if location:
            # 특정 공항만 조회
            response = table_notams.query(
                IndexName='data_source-issue_time-index',
                KeyConditionExpression=Key('data_source').eq(data_source) & Key('location').eq(location),
                Limit=limit,
                ScanIndexForward=False  # 최신순
            )
        else:
            # 전체 조회 (data_source별)
            filter_expression = Attr('data_source').eq(data_source)

            scan_kwargs = {
                'FilterExpression': filter_expression,
                'Limit': limit
            }

            if last_key:
                scan_kwargs['ExclusiveStartKey'] = json.loads(last_key)

            response = table_notams.scan(**scan_kwargs)

        items = response.get('Items', [])
        last_evaluated_key = response.get('LastEvaluatedKey')

        # 응답 생성
        result = {
            'status': 'success',
            'total': len(items),
            'data_source': data_source,
            'location': location,
            'data': items
        }

        if last_evaluated_key:
            result['last_key'] = json.dumps(last_evaluated_key, cls=DecimalEncoder)
            result['has_more'] = True

        return create_response(200, result)

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return create_response(500, {
            'status': 'error',
            'message': str(e)
        })


# ============================================================
# 2. GET /api/notams/{id} - 특정 NOTAM 조회
# ============================================================

def get_notam_detail(event, context):
    """
    특정 NOTAM 상세 조회

    경로 파라미터:
    - id: NOTAM 번호

    쿼리 파라미터:
    - location: 공항 코드 (필수)
    """
    try:
        # 경로 파라미터
        path_params = event.get('pathParameters') or {}
        notam_id = path_params.get('id')

        # 쿼리 파라미터
        query_params = event.get('queryStringParameters') or {}
        location = query_params.get('location')

        if not notam_id or not location:
            return create_response(400, {
                'status': 'error',
                'message': 'notam_id and location are required'
            })

        print(f"[INFO] NOTAM 상세 조회: {notam_id}, location={location}")

        # DynamoDB 조회
        response = table_notams.get_item(
            Key={
                'notam_id': notam_id,
                'location': location
            }
        )

        item = response.get('Item')

        if not item:
            return create_response(404, {
                'status': 'error',
                'message': 'NOTAM not found'
            })

        return create_response(200, {
            'status': 'success',
            'data': item
        })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return create_response(500, {
            'status': 'error',
            'message': str(e)
        })


# ============================================================
# 3. GET /api/stats - 통계 조회
# ============================================================

def get_statistics(event, context):
    """
    통계 조회

    쿼리 파라미터:
    - hours: 최근 몇 시간 (기본: 24)
    """
    try:
        # 쿼리 파라미터
        params = event.get('queryStringParameters') or {}
        hours = int(params.get('hours', 24))

        print(f"[INFO] 통계 조회: hours={hours}")

        # 시간 계산
        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        from_timestamp = now_timestamp - (hours * 3600)

        stats = {}

        # 각 data_source별 통계
        for data_source in ['domestic', 'international']:
            # NOTAM 개수
            response = table_notams.scan(
                FilterExpression=Attr('data_source').eq(data_source),
                Select='COUNT'
            )
            total_notams = response.get('Count', 0)

            # 크롤링 로그 (최근 N시간)
            log_response = table_logs.scan(
                FilterExpression=Attr('data_source').eq(data_source) & Attr('timestamp').gte(from_timestamp)
            )

            logs = log_response.get('Items', [])
            total_crawls = len(logs)
            successful_crawls = sum(1 for log in logs if log.get('status') == 'SUCCESS')
            success_rate = (successful_crawls / total_crawls * 100) if total_crawls > 0 else 0

            # 변경 이력 (최근 N시간)
            change_response = table_changes.scan(
                FilterExpression=Attr('data_source').eq(data_source) & Attr('timestamp').gte(from_timestamp)
            )
            changes = change_response.get('Items', [])

            # 변경 유형별 카운트
            change_counts = {
                'NEW': sum(1 for c in changes if c.get('change_type') == 'NEW'),
                'UPDATE': sum(1 for c in changes if c.get('change_type') == 'UPDATE'),
                'DELETE': sum(1 for c in changes if c.get('change_type') == 'DELETE')
            }

            stats[data_source] = {
                'total_notams': total_notams,
                'crawl_stats': {
                    'total_crawls': total_crawls,
                    'successful_crawls': successful_crawls,
                    'success_rate': round(success_rate, 2)
                },
                'changes': change_counts,
                'total_changes': sum(change_counts.values())
            }

        return create_response(200, {
            'status': 'success',
            'period_hours': hours,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': stats
        })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return create_response(500, {
            'status': 'error',
            'message': str(e)
        })


# ============================================================
# 4. POST /api/crawl - 수동 크롤링 트리거
# ============================================================

def trigger_manual_crawl(event, context):
    """
    수동 크롤링 트리거

    요청 본문 (JSON):
    {
      "data_source": "domestic",  // 선택 (기본: 둘 다)
      "hours_back": 24            // 선택 (기본: 24)
    }
    """
    try:
        # 요청 본문 파싱
        body = json.loads(event.get('body', '{}'))

        print(f"[INFO] 수동 크롤링 트리거: {body}")

        # 크롤러 Lambda 호출
        response = lambda_client.invoke(
            FunctionName=CRAWLER_LAMBDA_NAME,
            InvocationType='RequestResponse',  # 동기 호출
            Payload=json.dumps(body)
        )

        # 응답 파싱
        payload = json.loads(response['Payload'].read())

        if payload.get('statusCode') == 200:
            result_body = json.loads(payload['body'])

            return create_response(200, {
                'status': 'success',
                'message': 'Crawling completed',
                'result': result_body
            })
        else:
            return create_response(500, {
                'status': 'error',
                'message': 'Crawling failed',
                'details': payload
            })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return create_response(500, {
            'status': 'error',
            'message': str(e)
        })


# ============================================================
# 5. GET /api/changes - 변경 이력 조회
# ============================================================

def get_changes(event, context):
    """
    변경 이력 조회

    쿼리 파라미터:
    - data_source: domestic/international (선택)
    - change_type: NEW/UPDATE/DELETE (선택)
    - hours: 최근 몇 시간 (기본: 24)
    - limit: 최대 개수 (기본: 100)
    """
    try:
        # 쿼리 파라미터
        params = event.get('queryStringParameters') or {}
        data_source = params.get('data_source')
        change_type = params.get('change_type')
        hours = int(params.get('hours', 24))
        limit = min(int(params.get('limit', 100)), 1000)

        print(f"[INFO] 변경 이력 조회: data_source={data_source}, change_type={change_type}, hours={hours}")

        # 시간 계산
        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        from_timestamp = now_timestamp - (hours * 3600)

        # 필터 조건 생성
        filter_expression = Attr('timestamp').gte(from_timestamp)

        if data_source:
            filter_expression = filter_expression & Attr('data_source').eq(data_source)

        if change_type:
            filter_expression = filter_expression & Attr('change_type').eq(change_type)

        # DynamoDB 스캔
        response = table_changes.scan(
            FilterExpression=filter_expression,
            Limit=limit
        )

        items = response.get('Items', [])

        # 시간순 정렬
        items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        return create_response(200, {
            'status': 'success',
            'total': len(items),
            'period_hours': hours,
            'data_source': data_source,
            'change_type': change_type,
            'data': items
        })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return create_response(500, {
            'status': 'error',
            'message': str(e)
        })


# ============================================================
# 6. OPTIONS /* - CORS Preflight
# ============================================================

def options_handler(event, context):
    """CORS Preflight 요청 처리"""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': ''
    }


# ============================================================
# 메인 Lambda 핸들러 (라우터)
# ============================================================

def lambda_handler(event, context):
    """
    메인 Lambda 핸들러 - API Gateway 요청을 적절한 함수로 라우팅
    """
    # HTTP 메서드와 경로 추출
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    resource = event.get('resource', '/')

    # path와 resource 중 더 유용한 것 사용
    route = resource if (path == '/' or path == '') else path

    print(f"[INFO] {http_method} path={path}, resource={resource}, route={route}")

    # OPTIONS 요청 (CORS preflight)
    if http_method == 'OPTIONS':
        return options_handler(event, context)

    # GET 요청 라우팅
    if http_method == 'GET':
        if 'notams' in route or 'notams' in resource:
            # /notams/{id} 형식인지 확인
            path_parts = route.split('/')
            if len(path_parts) > 2 and path_parts[-1] and path_parts[-1] != 'notams':
                return get_notam_detail(event, context)
            else:
                return get_notams_list(event, context)
        elif 'stats' in route or 'stats' in resource:
            return get_statistics(event, context)
        elif 'changes' in route or 'changes' in resource:
            return get_changes(event, context)

    # POST 요청 라우팅
    if http_method == 'POST':
        if 'crawl' in route or 'crawl' in resource:
            return trigger_manual_crawl(event, context)

    # 매칭되는 경로가 없음
    return create_response(404, {
        'error': 'Not Found',
        'message': f'No handler for {http_method} route={route} (path={path}, resource={resource})'
    })


# ============================================================
# 로컬 테스트용
# ============================================================

if __name__ == '__main__':
    # 테스트 이벤트
    test_event = {
        'httpMethod': 'GET',
        'path': '/prod/notams',
        'resource': '/notams',
        'queryStringParameters': {
            'data_source': 'domestic',
            'limit': '10'
        }
    }

    # 테스트 실행
    result = lambda_handler(test_event, {})
    print(json.dumps(json.loads(result['body']), indent=2, ensure_ascii=False, cls=DecimalEncoder))
