#!/usr/bin/env python3
"""
Test DynamoDB access with EC2 IAM Role
"""
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

try:
    # DynamoDB 클라이언트 생성 (IAM Role 자동 사용)
    dynamodb = boto3.client('dynamodb', region_name='ap-southeast-2')

    print("✅ DynamoDB 연결 성공!")
    print("\n📋 테이블 목록:")

    # 테이블 리스트
    response = dynamodb.list_tables()
    tables = response.get('TableNames', [])

    if tables:
        for i, table in enumerate(tables, 1):
            print(f"  {i}. {table}")
    else:
        print("  (테이블 없음)")

    # NOTAM 관련 테이블 찾기
    notam_tables = [t for t in tables if 'notam' in t.lower() or 'NOTAM' in t]

    if notam_tables:
        print(f"\n🎯 NOTAM 테이블 발견: {notam_tables}")

        # 첫 번째 NOTAM 테이블의 아이템 수 확인
        table_name = notam_tables[0]
        table = boto3.resource('dynamodb', region_name='ap-southeast-2').Table(table_name)

        print(f"\n📊 {table_name} 테이블 정보:")
        print(f"  - 생성일: {table.creation_date_time}")
        print(f"  - 상태: {table.table_status}")

        # 샘플 데이터 스캔 (최대 10개)
        response = table.scan(Limit=10)
        items = response.get('Items', [])

        print(f"  - 샘플 아이템 수: {len(items)}개")

        if items:
            print(f"\n📄 첫 번째 아이템 샘플:")
            first_item = items[0]
            for key, value in list(first_item.items())[:5]:  # 처음 5개 필드만
                print(f"    {key}: {str(value)[:100]}")

except NoCredentialsError:
    print("❌ AWS 자격증명 없음 - IAM Role이 설정되지 않았습니다")
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'AccessDeniedException':
        print("❌ DynamoDB 접근 권한 없음")
        print("IAM Role에 DynamoDB 권한을 추가해야 합니다:")
        print("  - AmazonDynamoDBReadOnlyAccess (읽기만)")
        print("  또는")
        print("  - AmazonDynamoDBFullAccess (읽기/쓰기)")
    else:
        print(f"❌ 에러: {e}")
except Exception as e:
    print(f"❌ 예상치 못한 에러: {e}")
