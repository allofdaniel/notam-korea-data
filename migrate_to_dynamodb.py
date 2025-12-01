"""
SQLite → DynamoDB 마이그레이션 스크립트
로컬 SQLite 데이터를 AWS DynamoDB로 업로드
"""

import sqlite3
import boto3
from decimal import Decimal
import json

# AWS 설정
AWS_REGION = 'ap-southeast-2'  # 시드니
DYNAMODB_TABLE_NAME = 'NOTAM_Records'

# DynamoDB 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

def convert_float_to_decimal(obj):
    """float를 Decimal로 변환 (DynamoDB 호환)"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_float_to_decimal(v) for v in obj]
    return obj

def migrate_to_dynamodb(db_name='notam_realtime.db'):
    """SQLite → DynamoDB 마이그레이션"""

    print("=" * 60)
    print("SQLite → DynamoDB 마이그레이션")
    print("=" * 60)
    print()

    # SQLite 연결
    print(f"[1/3] SQLite 데이터베이스 연결: {db_name}")
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 데이터 읽기
    print("[2/3] NOTAM 데이터 읽기...")
    cursor.execute("""
        SELECT * FROM notam_records
        ORDER BY created_at DESC
    """)

    notams = cursor.fetchall()
    total = len(notams)

    print(f"  - 총 {total}개 레코드 발견")
    print()

    if total == 0:
        print("❌ 마이그레이션할 데이터가 없습니다.")
        return

    # DynamoDB에 업로드
    print(f"[3/3] DynamoDB에 업로드 중...")

    success_count = 0
    error_count = 0

    for idx, notam in enumerate(notams, 1):
        try:
            # Row 객체를 딕셔너리로 변환
            notam_dict = dict(notam)

            # DynamoDB 스키마에 맞게 매핑
            item = {
                'notam_id': notam_dict['notam_no'],  # notam_no → notam_id
                'location': notam_dict['location'],
                'notam_type': notam_dict['notam_type'],
                'status': notam_dict.get('status', 'ACTIVE'),
                'issue_time': notam_dict.get('issue_time', ''),
                'start_time': notam_dict.get('start_time', ''),
                'end_time': notam_dict.get('end_time', ''),
                'qcode': notam_dict.get('qcode', ''),
                'full_text': notam_dict.get('full_text', ''),
                'raw_data': notam_dict.get('raw_data', ''),
                'data_source': 'domestic' if notam_dict.get('airport_id') else 'international',
                'crawl_timestamp': notam_dict.get('created_at', ''),
            }

            # None 값 제거
            item = {k: v for k, v in item.items() if v is not None and v != ''}

            # float를 Decimal로 변환
            item = convert_float_to_decimal(item)

            # DynamoDB에 저장
            table.put_item(Item=item)

            success_count += 1

            # 진행률 표시
            if idx % 10 == 0 or idx == total:
                print(f"  - {idx}/{total} 업로드 완료 ({success_count} 성공, {error_count} 실패)")

        except Exception as e:
            error_count += 1
            print(f"  ! 오류 발생 (NOTAM ID: {item.get('notam_id', 'Unknown')}): {e}")

    conn.close()

    print()
    print("=" * 60)
    print("마이그레이션 완료!")
    print("=" * 60)
    print(f"  - 총 처리: {total}개")
    print(f"  - 성공: {success_count}개")
    print(f"  - 실패: {error_count}개")
    print()

    if success_count > 0:
        print("✅ 데이터 업로드 성공!")
        print()
        print("다음 단계:")
        print("  1. API 테스트:")
        print("     https://402p7v6m12.execute-api.ap-southeast-2.amazonaws.com/prod/notams")
        print()
        print("  2. v0 대시보드 연동")

    return success_count, error_count


if __name__ == '__main__':
    try:
        migrate_to_dynamodb()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print()
        print("AWS 자격 증명을 확인하세요:")
        print("  - AWS CLI 설치 여부")
        print("  - aws configure 설정 여부")
        print("  - 올바른 리전 설정 (ap-southeast-2)")
