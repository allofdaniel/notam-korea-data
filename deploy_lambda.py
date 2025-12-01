"""AWS Lambda 배포 스크립트"""
import boto3
import zipfile
import os
import json
import time

# AWS 클라이언트
lambda_client = boto3.client('lambda')
iam_client = boto3.client('iam')
events_client = boto3.client('events')

FUNCTION_NAME = 'notam-realtime-crawler'
ROLE_NAME = 'notam-lambda-role'
BUCKET_NAME = 'notam-korea-data'
BACKUP_BUCKET = 'notam-backup'

def create_iam_role():
    """Lambda용 IAM 역할 생성"""
    print("=" * 80)
    print("IAM 역할 생성 중...")
    print("=" * 80)
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    try:
        # 역할 생성
        response = iam_client.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='NOTAM Lambda Crawler Role'
        )
        role_arn = response['Role']['Arn']
        print(f"[OK] IAM 역할 생성: {role_arn}")
        
        # 정책 연결
        policies = [
            'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
            'arn:aws:iam::aws:policy/AmazonS3FullAccess'
        ]
        
        for policy_arn in policies:
            iam_client.attach_role_policy(
                RoleName=ROLE_NAME,
                PolicyArn=policy_arn
            )
            print(f"[OK] 정책 연결: {policy_arn}")
        
        # IAM 역할이 전파될 때까지 대기
        print("\n역할 전파 대기 (10초)...")
        time.sleep(10)
        
        return role_arn
    
    except iam_client.exceptions.EntityAlreadyExistsException:
        # 기존 역할 사용
        response = iam_client.get_role(RoleName=ROLE_NAME)
        role_arn = response['Role']['Arn']
        print(f"[OK] 기존 IAM 역할 사용: {role_arn}")
        return role_arn

def create_deployment_package():
    """Lambda 배포 패키지 생성"""
    print("\n" + "=" * 80)
    print("배포 패키지 생성 중...")
    print("=" * 80)
    
    zip_file = 'lambda_deployment.zip'
    
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write('lambda_notam_crawler.py', 'lambda_function.py')
    
    print(f"[OK] {zip_file} 생성 완료")
    
    # 파일 크기
    size = os.path.getsize(zip_file) / 1024
    print(f"파일 크기: {size:.2f} KB")
    
    return zip_file

def deploy_lambda_function(role_arn, zip_file):
    """Lambda 함수 배포"""
    print("\n" + "=" * 80)
    print("Lambda 함수 배포 중...")
    print("=" * 80)
    
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    try:
        # 새 함수 생성
        response = lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Timeout=300,
            MemorySize=512,
            Environment={
                'Variables': {
                    'BUCKET_NAME': BUCKET_NAME,
                    'BACKUP_BUCKET': BACKUP_BUCKET
                }
            },
            Description='실시간 NOTAM 크롤러'
        )
        print(f"[OK] Lambda 함수 생성: {response['FunctionArn']}")
        
    except lambda_client.exceptions.ResourceConflictException:
        # 기존 함수 업데이트
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content
        )
        print(f"[OK] Lambda 함수 업데이트: {response['FunctionArn']}")
        
        # 환경 변수 업데이트
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Environment={
                'Variables': {
                    'BUCKET_NAME': BUCKET_NAME,
                    'BACKUP_BUCKET': BACKUP_BUCKET
                }
            }
        )
    
    return response['FunctionArn']

def create_schedule(function_arn):
    """EventBridge 스케줄 생성"""
    print("\n" + "=" * 80)
    print("스케줄 설정 중...")
    print("=" * 80)
    
    rule_name = 'notam-crawler-schedule'
    
    try:
        # EventBridge 규칙 생성 (매 시간 실행)
        events_client.put_rule(
            Name=rule_name,
            ScheduleExpression='rate(1 hour)',  # 매 시간
            State='ENABLED',
            Description='NOTAM 크롤러 매 시간 실행'
        )
        print(f"[OK] 스케줄 생성: 매 시간 실행")
        
        # Lambda 권한 추가
        lambda_client.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId='AllowEventBridgeInvoke',
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=f'arn:aws:events:ap-northeast-2:{boto3.client("sts").get_caller_identity()["Account"]}:rule/{rule_name}'
        )
        
        # 타겟 추가
        events_client.put_targets(
            Rule=rule_name,
            Targets=[{
                'Id': '1',
                'Arn': function_arn
            }]
        )
        print(f"[OK] Lambda 함수 연결 완료")
        
    except Exception as e:
        print(f"[INFO] 스케줄 설정: {e}")

def test_function():
    """Lambda 함수 테스트"""
    print("\n" + "=" * 80)
    print("Lambda 함수 테스트 중...")
    print("=" * 80)
    
    response = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType='RequestResponse'
    )
    
    result = json.loads(response['Payload'].read())
    print(f"\n응답:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if response['StatusCode'] == 200:
        print("\n[OK] 테스트 성공!")
    else:
        print("\n[ERROR] 테스트 실패")

def main():
    print("=" * 80)
    print("AWS Lambda NOTAM Crawler 배포")
    print("=" * 80)
    
    # 1. IAM 역할
    role_arn = create_iam_role()
    
    # 2. 배포 패키지
    zip_file = create_deployment_package()
    
    # 3. Lambda 함수 배포
    function_arn = deploy_lambda_function(role_arn, zip_file)
    
    # 4. 스케줄 설정
    create_schedule(function_arn)
    
    # 5. 테스트
    print("\n함수 테스트 하시겠습니까? (y/n): ", end='')
    if input().lower() == 'y':
        test_function()
    
    print("\n" + "=" * 80)
    print("배포 완료!")
    print("=" * 80)
    print(f"\nLambda 함수: {FUNCTION_NAME}")
    print(f"스케줄: 매 시간 자동 실행")
    print(f"S3 버킷: {BUCKET_NAME}")
    print(f"백업 버킷: {BACKUP_BUCKET}")
    print("\n확인:")
    print("  1. AWS Console > Lambda > Functions")
    print(f"  2. {FUNCTION_NAME} 클릭")
    print("  3. 'Test' 버튼으로 수동 실행 가능")
    print("  4. CloudWatch Logs에서 로그 확인")
    print("=" * 80)

if __name__ == '__main__':
    main()
