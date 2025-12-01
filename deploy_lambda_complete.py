"""
Lambda 완전 NOTAM API 자동 배포 스크립트
"""
import boto3
import json
import time
import sys

# UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# AWS 클라이언트
lambda_client = boto3.client('lambda', region_name='ap-southeast-2')
apigateway = boto3.client('apigateway', region_name='ap-southeast-2')

FUNCTION_NAME = 'notam-query-complete'
ROLE_ARN = 'arn:aws:iam::496707410683:role/notam-lambda-role'
ZIP_FILE = 'lambda_notam_query_complete.zip'

def create_or_update_lambda():
    """Lambda 함수 생성 또는 업데이트"""
    print(f"[DEPLOY] Lambda 배포 패키지 로드 중: {ZIP_FILE}")

    with open(ZIP_FILE, 'rb') as f:
        zip_content = f.read()

    print(f"[DEPLOY] 패키지 크기: {len(zip_content) / 1024:.1f} KB")

    try:
        # 새로 생성 시도
        print(f"\n[CREATE] Lambda 함수 생성 중...")
        response = lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime='python3.11',
            Role=ROLE_ARN,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Timeout=300,
            MemorySize=512,
            Environment={
                'Variables': {
                    'BUCKET_NAME': 'notam-korea-data'
                }
            },
            Description='S3 154,986개 전체 NOTAM 조회 API'
        )
        print(f"[OK] Lambda 함수 생성 완료!")

    except Exception as e:
        if 'ResourceConflictException' in str(e) or 'already exists' in str(e):
            # 이미 존재하면 업데이트
            print(f"[UPDATE] 함수가 이미 존재합니다. 코드 업데이트 중...")
            response = lambda_client.update_function_code(
                FunctionName=FUNCTION_NAME,
                ZipFile=zip_content
            )
            # 설정 업데이트
            lambda_client.update_function_configuration(
                FunctionName=FUNCTION_NAME,
                Timeout=300,
                MemorySize=512,
                Environment={
                    'Variables': {
                        'BUCKET_NAME': 'notam-korea-data'
                    }
                }
            )
            print(f"[OK] Lambda 함수 업데이트 완료!")
        else:
            raise

    print(f"[INFO] Function ARN: {response['FunctionArn']}")
    return response

def add_api_gateway_permission():
    """API Gateway에서 Lambda 호출 권한 부여"""
    print(f"\n[PERMISSION] API Gateway 권한 설정 중...")

    statement_id = 'apigateway-notam-complete'

    try:
        lambda_client.remove_permission(
            FunctionName=FUNCTION_NAME,
            StatementId=statement_id
        )
    except:
        pass

    lambda_client.add_permission(
        FunctionName=FUNCTION_NAME,
        StatementId=statement_id,
        Action='lambda:InvokeFunction',
        Principal='apigateway.amazonaws.com',
        SourceArn='arn:aws:execute-api:ap-southeast-2:496707410683:k9cp26l1ra/*'
    )

    print(f"[OK] API Gateway 권한 추가 완료!")

def setup_api_gateway():
    """API Gateway 엔드포인트 설정"""
    print(f"\n[GATEWAY] API Gateway 설정 중...")

    # 기존 API ID (notam-api)
    api_id = 'k9cp26l1ra'

    # 루트 리소스 찾기
    resources = apigateway.get_resources(restApiId=api_id)
    root_id = None
    notams_resource_id = None

    for resource in resources['items']:
        if resource['path'] == '/':
            root_id = resource['id']
        if resource['path'] == '/notams':
            notams_resource_id = resource['id']

    if not notams_resource_id:
        print("[ERROR] /notams 리소스를 찾을 수 없습니다.")
        return

    print(f"[OK] /notams 리소스 찾음: {notams_resource_id}")

    # 새 엔드포인트 생성
    endpoints = ['stats', 'active', 'expired', 'trigger', 'complete']

    for endpoint in endpoints:
        try:
            # 리소스 생성
            print(f"  [CREATE] /{endpoint} 리소스 생성 중...")
            resource_response = apigateway.create_resource(
                restApiId=api_id,
                parentId=notams_resource_id,
                pathPart=endpoint
            )
            resource_id = resource_response['id']

            # GET 메서드 생성
            apigateway.put_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='GET',
                authorizationType='NONE'
            )

            # Lambda 통합
            lambda_arn = f'arn:aws:lambda:ap-southeast-2:496707410683:function:{FUNCTION_NAME}'
            apigateway.put_integration(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='GET',
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f'arn:aws:apigateway:ap-southeast-2:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
            )

            print(f"  [OK] /{endpoint} 엔드포인트 생성 완료")

        except apigateway.exceptions.ConflictException:
            print(f"  [INFO] /{endpoint} 이미 존재함 (스킵)")
        except Exception as e:
            print(f"  [WARN] /{endpoint} 생성 실패: {e}")

    # /date/{date} 엔드포인트 생성
    try:
        print(f"  [CREATE] /date 리소스 생성 중...")
        date_parent = apigateway.create_resource(
            restApiId=api_id,
            parentId=notams_resource_id,
            pathPart='date'
        )

        date_resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=date_parent['id'],
            pathPart='{date}'
        )

        apigateway.put_method(
            restApiId=api_id,
            resourceId=date_resource['id'],
            httpMethod='GET',
            authorizationType='NONE'
        )

        lambda_arn = f'arn:aws:lambda:ap-southeast-2:496707410683:function:{FUNCTION_NAME}'
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=date_resource['id'],
            httpMethod='GET',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=f'arn:aws:apigateway:ap-southeast-2:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
        )

        print(f"  [OK] /date/{{date}} 엔드포인트 생성 완료")
    except apigateway.exceptions.ConflictException:
        print(f"  [INFO] /date/{{date}} 이미 존재함 (스킵)")
    except Exception as e:
        print(f"  [WARN] /date/{{date}} 생성 실패: {e}")

def deploy_api():
    """API 배포"""
    print(f"\n[DEPLOY] API 배포 중...")

    api_id = 'k9cp26l1ra'

    apigateway.create_deployment(
        restApiId=api_id,
        stageName='prod',
        description='Complete NOTAM API deployment'
    )

    print(f"[OK] API 배포 완료!")
    print(f"\n[URL] API URL: https://{api_id}.execute-api.ap-southeast-2.amazonaws.com/prod")

if __name__ == '__main__':
    print("=" * 60)
    print("Lambda 완전 NOTAM API 자동 배포")
    print("=" * 60)

    try:
        # 1. Lambda 함수 배포
        create_or_update_lambda()

        # 2. API Gateway 권한
        add_api_gateway_permission()

        # 3. API Gateway 엔드포인트 설정
        setup_api_gateway()

        # 4. API 배포
        deploy_api()

        print("\n" + "=" * 60)
        print("[SUCCESS] 배포 완료!")
        print("=" * 60)

        print("\n[TEST] 테스트 명령:")
        print('curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/stats"')
        print('curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/active"')

    except Exception as e:
        print(f"\n[ERROR] 배포 실패: {e}")
        import traceback
        traceback.print_exc()
