"""AWS Lambda: 실시간 NOTAM 크롤러"""
import json
import boto3
import requests
from datetime import datetime, timedelta
import os

# S3 클라이언트
s3 = boto3.client('s3')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'notam-korea-data')

def crawl_today_notams():
    """오늘 NOTAM 크롤링"""
    url = "https://aim.koca.go.kr/xNotam/searchAllNotam.do"
    
    # 오늘 날짜
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    
    all_notams = []
    
    # 국내(D) + 국제(I)
    for data_source in ['D', 'I']:
        payload = {
            'sch_inorout': data_source,
            'sch_airport': '',
            'sch_from_date': date_str,
            'sch_from_time': '0000',
            'sch_to_date': date_str,
            'sch_to_time': '2359',
            'sch_series_type': 'A,C,D,E,G,Z,SNOWTAM',
            'sch_fir': '',
            'ibsheetPageNo': '1',
            'ibsheetRowPerPage': '100'
        }
        
        try:
            response = requests.post(url, data=payload, timeout=30)
            data = response.json()
            
            if 'DATA' in data and data['DATA']:
                for item in data['DATA']:
                    notam = {
                        'notam_number': item.get('NOTAM_NO', ''),
                        'location': item.get('LOCATION', ''),
                        'series': item.get('SERIES', ''),
                        'qcode': item.get('QCODE', ''),
                        'qcode_mean': item.get('QCODE_MEAN', ''),
                        'issue_time': item.get('ISSUE_TIME', ''),
                        'effective_start': item.get('EFFECTIVESTART', ''),
                        'effective_end': item.get('EFFECTIVEEND', ''),
                        'e_text': item.get('ECODE', ''),
                        'full_text': item.get('FULL_TEXT', ''),
                        'fir': item.get('FIR', ''),
                        'ais_type': item.get('AIS_TYPE', ''),
                        'crawl_date': date_str,
                        'crawl_timestamp': today.isoformat(),
                        'data_source': data_source
                    }
                    all_notams.append(notam)
        
        except Exception as e:
            print(f"Error crawling {data_source}: {e}")
    
    return all_notams

def save_to_s3(notams, bucket_name):
    """S3에 저장"""
    if not notams:
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # 파일명: notam_realtime/2024-12-01/notam_20241201_100000.json
    s3_key = f'notam_realtime/{date_str}/notam_{timestamp}.json'
    
    # JSON으로 변환
    json_data = json.dumps(notams, ensure_ascii=False, indent=2)
    
    # S3 업로드
    s3.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=json_data.encode('utf-8'),
        ContentType='application/json'
    )
    
    return s3_key

def lambda_handler(event, context):
    """Lambda 핸들러"""
    print(f"Starting NOTAM crawl at {datetime.now().isoformat()}")
    
    # 크롤링
    notams = crawl_today_notams()
    
    if not notams:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'No NOTAMs found',
                'count': 0
            })
        }
    
    # S3에 저장
    s3_key = save_to_s3(notams, BUCKET_NAME)
    
    # 백업 버킷에도 저장 (선택사항)
    backup_bucket = os.environ.get('BACKUP_BUCKET', 'notam-backup')
    try:
        save_to_s3(notams, backup_bucket)
    except:
        pass
    
    print(f"Saved {len(notams)} NOTAMs to s3://{BUCKET_NAME}/{s3_key}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Success',
            'count': len(notams),
            's3_key': s3_key,
            'bucket': BUCKET_NAME
        })
    }

# 로컬 테스트용
if __name__ == '__main__':
    result = lambda_handler({}, {})
    print(json.dumps(result, indent=2))
