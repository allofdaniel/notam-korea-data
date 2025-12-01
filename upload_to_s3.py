#!/usr/bin/env python3
"""
NOTAM 데이터를 S3에 업로드
"""
import boto3
import sqlite3
import json
import sys
import os
from datetime import datetime

def export_to_json(db_path='notam_realtime.db', output_file='notam_data.json'):
    """SQLite DB를 JSON으로 변환"""
    print(f"DB에서 데이터 추출 중: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM notams ORDER BY b_start_time")
    rows = cursor.fetchall()

    # Row 객체를 dict로 변환
    data = []
    for row in rows:
        data.append(dict(row))

    conn.close()

    print(f"총 {len(data):,}개 NOTAM 추출")

    # JSON 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
    print(f"JSON 파일 생성: {output_file} ({file_size:.2f} MB)")
    return output_file, len(data)

def upload_to_s3(file_path, bucket_name, s3_key=None):
    """파일을 S3에 업로드"""
    if s3_key is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f'notam_data_{timestamp}.json'

    print(f"\nS3 업로드 중...")
    print(f"  버킷: {bucket_name}")
    print(f"  키: {s3_key}")

    try:
        s3 = boto3.client('s3')
        s3.upload_file(
            file_path, 
            bucket_name, 
            s3_key,
            ExtraArgs={'ContentType': 'application/json'}
        )

        print(f"[OK] 업로드 완료!")
        print(f"  S3 URI: s3://{bucket_name}/{s3_key}")

        # S3 URL
        region = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
        if region:
            url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        else:
            url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        print(f"  URL: {url}")

        return True
    except Exception as e:
        print(f"[ERROR] 업로드 실패: {e}")
        return False

def main():
    print("=" * 80)
    print("NOTAM 데이터 S3 업로드")
    print("=" * 80)

    # S3 버킷 이름 (환경 변수 또는 인자)
    bucket_name = os.environ.get('S3_BUCKET')
    if not bucket_name and len(sys.argv) > 1:
        bucket_name = sys.argv[1]

    if not bucket_name:
        bucket_name = input("\nS3 버킷 이름을 입력하세요: ").strip()

    if not bucket_name:
        print("[ERROR] 버킷 이름이 필요합니다.")
        sys.exit(1)

    # DB 확인
    try:
        conn = sqlite3.connect('notam_realtime.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notams")
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(b_start_time), MAX(b_start_time) FROM notams")
        date_range = cursor.fetchone()
        
        conn.close()

        print(f"\n현재 DB 상태:")
        print(f"  총 NOTAM: {count:,}개")
        print(f"  날짜 범위: {date_range[0]} ~ {date_range[1]}")

        if count == 0:
            print("[ERROR] 데이터가 없습니다!")
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] DB 오류: {e}")
        sys.exit(1)

    # JSON 변환
    json_file, total_records = export_to_json()

    # S3 업로드
    success = upload_to_s3(json_file, bucket_name)

    if success:
        print("\n" + "=" * 80)
        print("완료!")
        print("=" * 80)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
