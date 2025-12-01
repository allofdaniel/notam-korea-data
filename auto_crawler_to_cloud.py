"""
자동 NOTAM 크롤러 → DynamoDB 업로드
기존 작동하는 notam_crawler_api.py 기반

작성일: 2025-11-13
용도: Windows Task Scheduler로 자동 실행
"""

import boto3
import sqlite3
import sys
import os
from datetime import datetime

# Windows 한국어 환경 인코딩 설정
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'detach'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    except:
        pass

# AWS 설정
AWS_REGION = 'ap-southeast-2'
DYNAMODB_TABLE_NAME = 'NOTAM_Records'

# DynamoDB 클라이언트
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


def crawl_and_upload():
    """크롤링 실행 → SQLite 저장 → DynamoDB 업로드"""

    print("=" * 60)
    print("자동 NOTAM 크롤러 시작")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # 1. 기존 크롤러 실행 (SQLite에 저장)
    print("[1/3] NOTAM 크롤링 중...")
    try:
        from notam_crawler_api import NOTAMCrawlerAPI

        crawler = NOTAMCrawlerAPI()

        # 국내 NOTAM 크롤링 (2시간 전부터)
        domestic_result = crawler.crawl_notam_api(data_source='domestic', hours_back=2)

        print(f"  ✅ {domestic_result['records_found']}개 발견, {domestic_result['records_saved']}개 저장")

    except Exception as e:
        print(f"  ❌ 크롤링 오류: {e}")
        return

    print()

    # 2. SQLite에서 데이터 읽기
    print("[2/3] SQLite 데이터 읽기...")
    conn = sqlite3.connect('notam_realtime.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 최근 24시간 데이터만 가져오기
    cursor.execute("""
        SELECT * FROM notam_records
        WHERE datetime(created_at) >= datetime('now', '-24 hours')
        ORDER BY created_at DESC
    """)

    notams = cursor.fetchall()
    print(f"  ✅ {len(notams)}개 레코드 읽기 완료")
    print()

    if len(notams) == 0:
        print("[WARN] 업로드할 데이터 없음")
        conn.close()
        return

    # 3. DynamoDB에 업로드
    print("[3/3] DynamoDB 업로드 중...")
    uploaded_count = 0
    error_count = 0

    for notam in notams:
        try:
            notam_dict = dict(notam)

            # DynamoDB 스키마에 맞게 매핑
            item = {
                'notam_id': notam_dict['notam_no'],
                'location': notam_dict.get('location', ''),
                'notam_type': notam_dict.get('notam_type', ''),
                'status': 'ACTIVE',
                'issue_time': notam_dict.get('issue_time', ''),
                'start_time': notam_dict.get('start_time', ''),
                'end_time': notam_dict.get('end_time', ''),
                'qcode': notam_dict.get('qcode', ''),
                'full_text': notam_dict.get('full_text', ''),
                'data_source': 'domestic',
                'crawl_timestamp': notam_dict.get('created_at', '')
            }

            # None 값 제거
            item = {k: v for k, v in item.items() if v is not None and v != ''}

            # DynamoDB에 저장
            table.put_item(Item=item)
            uploaded_count += 1

        except Exception as e:
            error_count += 1
            print(f"  ! 오류: {item.get('notam_id', 'Unknown')} - {e}")

    conn.close()

    print(f"  ✅ {uploaded_count}/{len(notams)}개 업로드 완료")

    if error_count > 0:
        print(f"  ⚠️ {error_count}개 오류 발생")

    print()
    print("=" * 60)
    print("✅ 자동 크롤링 완료!")
    print("=" * 60)


if __name__ == '__main__':
    try:
        crawl_and_upload()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

        # 오류 로그
        with open('crawler_error.log', 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()}: {e}\n")
