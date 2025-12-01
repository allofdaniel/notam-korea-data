"""
S3 버킷 생성 및 설정 스크립트
상업용 NOTAM 서비스를 위한 S3 저장소 생성
"""

import boto3
import json
from datetime import datetime

# AWS 설정
AWS_REGION = 'ap-southeast-2'  # 시드니
BUCKET_NAME = f'notam-storage-{datetime.now().strftime("%Y%m%d")}'

def create_s3_bucket():
    """S3 버킷 생성 및 설정"""

    print("=" * 60)
    print("S3 버킷 생성 및 설정")
    print("=" * 60)
    print()

    s3_client = boto3.client('s3', region_name=AWS_REGION)

    try:
        # 1. S3 버킷 생성
        print(f"[1/4] S3 버킷 생성 중: {BUCKET_NAME}")

        # ap-southeast-2 리전에서는 LocationConstraint 필요
        s3_client.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={
                'LocationConstraint': AWS_REGION
            }
        )
        print(f"  ✅ S3 버킷 생성 완료: {BUCKET_NAME}")
        print()

        # 2. 버킷 버전 관리 활성화
        print("[2/4] 버전 관리 활성화 중...")
        s3_client.put_bucket_versioning(
            Bucket=BUCKET_NAME,
            VersioningConfiguration={
                'Status': 'Enabled'
            }
        )
        print("  ✅ 버전 관리 활성화 완료")
        print()

        # 3. 수명 주기 정책 설정 (90일 후 Glacier로 이동, 365일 후 삭제)
        print("[3/4] 수명 주기 정책 설정 중...")
        lifecycle_policy = {
            'Rules': [
                {
                    'Id': 'Archive old NOTAMs',
                    'Status': 'Enabled',
                    'Prefix': 'notams/',
                    'Transitions': [
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER'
                        }
                    ],
                    'Expiration': {
                        'Days': 365
                    }
                }
            ]
        }

        s3_client.put_bucket_lifecycle_configuration(
            Bucket=BUCKET_NAME,
            LifecycleConfiguration=lifecycle_policy
        )
        print("  ✅ 수명 주기 정책 설정 완료")
        print("     - 90일 후 Glacier로 이동")
        print("     - 365일 후 자동 삭제")
        print()

        # 4. 버킷 정책 설정 (Lambda에서 접근 가능하도록)
        print("[4/4] 버킷 정책 설정 중...")
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowLambdaAccess",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{BUCKET_NAME}/*",
                        f"arn:aws:s3:::{BUCKET_NAME}"
                    ]
                }
            ]
        }

        s3_client.put_bucket_policy(
            Bucket=BUCKET_NAME,
            Policy=json.dumps(bucket_policy)
        )
        print("  ✅ 버킷 정책 설정 완료")
        print()

        # 완료
        print("=" * 60)
        print("S3 버킷 생성 완료!")
        print("=" * 60)
        print()
        print(f"📦 버킷 이름: {BUCKET_NAME}")
        print(f"📍 리전: {AWS_REGION}")
        print(f"🔗 URL: https://s3.console.aws.amazon.com/s3/buckets/{BUCKET_NAME}")
        print()
        print("다음 단계:")
        print("  1. Lambda 함수에 S3 업로드 권한 추가")
        print("  2. Lambda 환경 변수에 S3_BUCKET_NAME 추가")
        print("  3. Lambda 코드에 S3 저장 로직 활성화")
        print()

        return BUCKET_NAME

    except s3_client.exceptions.BucketAlreadyExists:
        print(f"❌ 오류: 버킷 이름 '{BUCKET_NAME}'이 이미 존재합니다.")
        print("   다른 이름을 시도하세요.")
        return None

    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        print(f"✅ 버킷 '{BUCKET_NAME}'이 이미 존재합니다.")
        print("   기존 버킷을 사용합니다.")
        return BUCKET_NAME

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print()
        print("AWS 자격 증명 및 권한을 확인하세요:")
        print("  - S3 버킷 생성 권한")
        print("  - 올바른 리전 설정")
        return None


if __name__ == '__main__':
    bucket_name = create_s3_bucket()

    if bucket_name:
        print(f"\n✅ S3 버킷 준비 완료: {bucket_name}")

        # 환경 변수 파일 생성
        with open('s3_config.txt', 'w') as f:
            f.write(f"S3_BUCKET_NAME={bucket_name}\n")
            f.write(f"AWS_REGION={AWS_REGION}\n")

        print("\n📄 설정 파일 저장됨: s3_config.txt")
