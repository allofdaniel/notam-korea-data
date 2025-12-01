# AWS Lambda 수동 설정 (5분 완료)

권한 오류 시 AWS Console에서 직접 설정하는 방법입니다.

## 🎯 단계별 가이드

### 1단계: Lambda 함수 생성 (2분)

1. **AWS Console 접속**: https://console.aws.amazon.com
2. **Lambda 서비스** 검색 후 이동
3. **Create function** 클릭
4. 설정:
   - **Function name**: `notam-realtime-crawler`
   - **Runtime**: Python 3.11
   - **Architecture**: x86_64
   - **Permissions**: Use an existing role
   - **Existing role**: `notam-lambda-role` 선택
5. **Create function** 클릭

### 2단계: 코드 업로드 (1분)

1. 함수 생성 후 **Code** 탭
2. 아래 코드를 **lambda_function.py**에 복사 붙여넣기:

```python
"""AWS Lambda: 실시간 NOTAM 크롤러"""
import json
import boto3
import urllib.request
import urllib.parse
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = 'notam-korea-data'
BACKUP_BUCKET = 'notam-backup'

def crawl_today_notams():
    url = "https://aim.koca.go.kr/xNotam/searchAllNotam.do"
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    all_notams = []
    
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
            data_bytes = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, method='POST')
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
            
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
            print(f"Error: {e}")
    
    return all_notams

def lambda_handler(event, context):
    print(f"Starting NOTAM crawl at {datetime.now().isoformat()}")
    
    notams = crawl_today_notams()
    
    if not notams:
        return {'statusCode': 200, 'body': json.dumps({'message': 'No NOTAMs', 'count': 0})}
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    date_str = datetime.now().strftime('%Y-%m-%d')
    s3_key = f'notam_realtime/{date_str}/notam_{timestamp}.json'
    
    json_data = json.dumps(notams, ensure_ascii=False, indent=2)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=json_data.encode('utf-8'), ContentType='application/json')
    
    try:
        s3.put_object(Bucket=BACKUP_BUCKET, Key=s3_key, Body=json_data.encode('utf-8'), ContentType='application/json')
    except:
        pass
    
    print(f"Saved {len(notams)} NOTAMs to s3://{BUCKET_NAME}/{s3_key}")
    
    return {'statusCode': 200, 'body': json.dumps({'message': 'Success', 'count': len(notams), 's3_key': s3_key})}
```

3. **Deploy** 버튼 클릭

### 3단계: 설정 변경 (1분)

1. **Configuration** 탭 → **General configuration** → **Edit**
2. 설정:
   - **Timeout**: 5분 (300초)
   - **Memory**: 512 MB
3. **Save**

### 4단계: 테스트 (1분)

1. **Test** 탭
2. **Test event action**: Create new event
3. **Event name**: test
4. **Event JSON**: 그대로 두고
5. **Save**
6. **Test** 버튼 클릭

**성공하면**:
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Success\", \"count\": 150, \"s3_key\": \"notam_realtime/2024-12-01/notam_20241201_120000.json\"}"
}
```

### 5단계: 스케줄 설정 (1분)

1. **Configuration** 탭 → **Triggers**
2. **Add trigger** 클릭
3. **Select a source**: EventBridge (CloudWatch Events)
4. **Rule**: Create a new rule
5. 설정:
   - **Rule name**: `notam-hourly-schedule`
   - **Rule type**: Schedule expression
   - **Schedule expression**: `rate(1 hour)`
6. **Add** 클릭

## ✅ 완료!

이제 Lambda가 **매 시간 자동으로**:
1. 국내 + 국제 모든 NOTAM 수집
2. S3에 저장: `s3://notam-korea-data/notam_realtime/`

## 🔍 확인

### S3 확인
```
s3://notam-korea-data/notam_realtime/
  └── 2024-12-01/
      ├── notam_20241201_120000.json
      ├── notam_20241201_130000.json
      └── ...
```

### CloudWatch Logs
Lambda > Monitor > View logs in CloudWatch

## 🎯 스케줄 변경 (선택사항)

다른 스케줄로 변경하려면:

**매 30분**:
```
rate(30 minutes)
```

**매일 오전 9시 (KST = UTC+9, 즉 UTC 0시)**:
```
cron(0 0 * * ? *)
```

**매시간 정각**:
```
rate(1 hour)
```

Configuration > Triggers > Edit에서 변경

## 🎉 끝!

이제 자동으로 계속 NOTAM이 S3에 쌓입니다!
