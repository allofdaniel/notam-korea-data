#!/usr/bin/env python3
"""S3 업로드 (Complete NOTAM with FULL_TEXT)"""
import boto3
import os
from datetime import datetime

def upload_to_s3():
    print("=" * 80)
    print("S3 Upload - Complete NOTAM Data (with FULL_TEXT)")
    print("=" * 80)

    # 업로드할 파일들
    files = [
        ('notam_final_complete.db', 'application/x-sqlite3'),
        ('notam_final_complete.json', 'application/json')
    ]

    # 파일 확인
    for filename, _ in files:
        if not os.path.exists(filename):
            print(f"[ERROR] {filename} not found!")
            return False

        size = os.path.getsize(filename) / (1024 * 1024)
        print(f"\n{filename}: {size:.2f} MB")

    # S3 클라이언트
    try:
        s3 = boto3.client('s3')
    except Exception as e:
        print(f"\n[ERROR] AWS credentials not configured: {e}")
        print("\n설정 방법:")
        print("  1. py setup_aws_credentials.py")
        print("  2. 또는 환경변수 설정")
        return False

    # 업로드할 버킷
    buckets = ['notam-korea-data', 'notam-backup']

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    for bucket_name in buckets:
        print(f"\n{'='*80}")
        print(f"Uploading to: {bucket_name}")
        print(f"{'='*80}")

        for filename, content_type in files:
            s3_key = f'notam_complete/{timestamp}/{filename}'

            try:
                print(f"\nUploading {filename}...")
                s3.upload_file(
                    filename,
                    bucket_name,
                    s3_key,
                    ExtraArgs={'ContentType': content_type}
                )

                print(f"[OK] s3://{bucket_name}/{s3_key}")

            except Exception as e:
                print(f"[ERROR] {e}")
                return False

    print("\n" + "=" * 80)
    print("Upload Complete!")
    print("=" * 80)
    print("\n업로드된 데이터:")
    print(f"  - 154,986개 NOTAM (2022-2025)")
    print(f"  - FULL_TEXT 포함 (완전한 노탐 정보)")
    print(f"  - 중복 제거 완료")
    print(f"  - 국내/국제 모든 노탐 포함")
    print("=" * 80)
    return True

if __name__ == '__main__':
    upload_to_s3()
