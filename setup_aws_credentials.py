#!/usr/bin/env python3
"""AWS 자격 증명 설정"""
import os
import json

print("=" * 80)
print("AWS 자격 증명 설정")
print("=" * 80)

print("\n필요한 정보:")
print("  1. AWS Access Key ID")
print("  2. AWS Secret Access Key")
print("  3. Region (선택사항, 기본: ap-northeast-2)")

print("\n" + "=" * 80)
print("AWS Access Key 발급 방법:")
print("=" * 80)
print("1. AWS Console 로그인 (https://console.aws.amazon.com)")
print("2. 우측 상단 계정명 클릭 > 'Security credentials'")
print("3. 'Access keys' 섹션에서 'Create access key' 클릭")
print("4. Access Key ID와 Secret Access Key 복사")
print("=" * 80)

print("\n자격 증명을 입력하세요:")
access_key = input("AWS Access Key ID: ").strip()
secret_key = input("AWS Secret Access Key: ").strip()
region = input("AWS Region (Enter = ap-northeast-2): ").strip() or "ap-northeast-2"

if not access_key or not secret_key:
    print("\n[ERROR] Access Key ID와 Secret Access Key는 필수입니다!")
    exit(1)

# AWS credentials 디렉토리 생성
aws_dir = os.path.expanduser("~/.aws")
os.makedirs(aws_dir, exist_ok=True)

# credentials 파일 작성
credentials_path = os.path.join(aws_dir, "credentials")
with open(credentials_path, 'w') as f:
    f.write("[default]\n")
    f.write(f"aws_access_key_id = {access_key}\n")
    f.write(f"aws_secret_access_key = {secret_key}\n")

# config 파일 작성
config_path = os.path.join(aws_dir, "config")
with open(config_path, 'w') as f:
    f.write("[default]\n")
    f.write(f"region = {region}\n")

print("\n" + "=" * 80)
print("설정 완료!")
print("=" * 80)
print(f"\n저장 위치:")
print(f"  - {credentials_path}")
print(f"  - {config_path}")

# 검증
print("\n" + "=" * 80)
print("연결 테스트 중...")
print("=" * 80)

try:
    import boto3
    s3 = boto3.client('s3')
    
    # 버킷 리스트 조회 시도
    response = s3.list_buckets()
    buckets = [b['Name'] for b in response['Buckets']]
    
    print("\n[OK] AWS 연결 성공!")
    print(f"\n사용 가능한 버킷 ({len(buckets)}개):")
    for bucket in buckets:
        print(f"  - {bucket}")
    
    # notam 버킷 확인
    target_buckets = ['notam-korea-data', 'notam-backup']
    existing = [b for b in target_buckets if b in buckets]
    missing = [b for b in target_buckets if b not in buckets]
    
    if existing:
        print(f"\n✅ 발견된 NOTAM 버킷:")
        for b in existing:
            print(f"  - {b}")
    
    if missing:
        print(f"\n⚠️  없는 버킷 (생성 필요):")
        for b in missing:
            print(f"  - {b}")
        print("\n버킷 생성 방법:")
        print("  1. AWS Console > S3")
        print("  2. 'Create bucket' 클릭")
        print(f"  3. 버킷 이름 입력: {missing[0]}")
        print(f"  4. Region: {region}")
        print("  5. 'Create bucket' 클릭")
    
    print("\n" + "=" * 80)
    print("다음 단계:")
    print("=" * 80)
    if missing:
        print("1. 없는 버킷 생성 (위 방법 참조)")
        print("2. py upload_complete_to_s3.py  # S3 업로드")
    else:
        print("py upload_complete_to_s3.py  # S3 업로드")
    print("=" * 80)

except ImportError:
    print("\n[INFO] boto3 설치 필요")
    print("설치 명령: pip install boto3")
    print("\n설치 후:")
    print("  py upload_complete_to_s3.py")

except Exception as e:
    print(f"\n[ERROR] 연결 실패: {e}")
    print("\n확인 사항:")
    print("  1. Access Key가 올바른지 확인")
    print("  2. IAM 정책에 S3 권한이 있는지 확인")
    print("  3. 인터넷 연결 확인")
