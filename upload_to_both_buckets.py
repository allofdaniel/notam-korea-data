#!/usr/bin/env python3
"""
NOTAM 데이터를 2개의 S3 버킷에 업로드
- notam-korea-data (메인)
- notam-backup (백업)
"""
import boto3
import json
import os
from datetime import datetime

def upload_to_s3(file_path, bucket_name, s3_key):
    """파일을 S3에 업로드"""
    print(f"\n{'='*80}")
    print(f"S3 업로드 중: {bucket_name}")
    print(f"{'='*80}")
    print(f"  파일: {file_path}")
    print(f"  버킷: {bucket_name}")
    print(f"  키: {s3_key}")

    try:
        s3 = boto3.client('s3')

        # 파일 업로드
        s3.upload_file(
            file_path,
            bucket_name,
            s3_key,
            ExtraArgs={'ContentType': 'application/json'}
        )

        print(f"\n[OK] 업로드 완료!")
        print(f"  S3 URI: s3://{bucket_name}/{s3_key}")

        # S3 URL 생성
        try:
            region = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
            if region:
                url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
            else:
                url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
            print(f"  URL: {url}")
        except:
            print(f"  URL: s3://{bucket_name}/{s3_key}")

        return True

    except Exception as e:
        print(f"\n[ERROR] 업로드 실패: {e}")
        return False

def main():
    print("=" * 80)
    print("NOTAM 데이터 S3 업로드 (2개 버킷)")
    print("=" * 80)

    # 업로드할 파일
    json_file = 'notam_data.json'

    if not os.path.exists(json_file):
        print(f"\n[ERROR] {json_file} 파일을 찾을 수 없습니다!")
        return False

    # 파일 정보
    file_size = os.path.getsize(json_file) / (1024 * 1024)  # MB
    print(f"\n업로드 파일: {json_file}")
    print(f"파일 크기: {file_size:.2f} MB")

    # JSON에서 레코드 수 확인
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"NOTAM 개수: {len(data):,}개")
    except Exception as e:
        print(f"[WARN] JSON 파싱 실패: {e}")

    # S3 키 이름 (타임스탬프 포함)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    s3_key = f'notam_data_{timestamp}.json'

    # 업로드할 버킷 목록
    buckets = [
        'notam-korea-data',  # 메인 데이터
        'notam-backup'       # 백업
    ]

    # 각 버킷에 업로드
    success_count = 0
    for bucket_name in buckets:
        if upload_to_s3(json_file, bucket_name, s3_key):
            success_count += 1

    # 결과 요약
    print("\n" + "=" * 80)
    if success_count == len(buckets):
        print(f"[완료] 모든 버킷 업로드 성공! ({success_count}/{len(buckets)})")
    elif success_count > 0:
        print(f"[부분 완료] 일부 버킷 업로드 성공 ({success_count}/{len(buckets)})")
    else:
        print(f"[실패] 모든 버킷 업로드 실패")
    print("=" * 80)

    return success_count > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
