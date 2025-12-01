# AWS Lambda 실시간 NOTAM 크롤러 설정 가이드

## 🎯 목표

AWS Lambda를 사용하여 실시간으로 NOTAM을 자동 수집하고 S3에 저장

## 📋 특징

- ✅ **완전 자동화**: 로컬 컴퓨터 불필요
- ✅ **서버리스**: 서버 관리 불필요
- ✅ **비용 효율**: 실행할 때만 과금
- ✅ **확장 가능**: 스케줄 자유롭게 조정
- ✅ **실시간**: 매 시간/매일 자동 실행

## 🏗️ 아키텍처

```
EventBridge (스케줄)
    ↓
Lambda 함수 (크롤러)
    ↓
NOTAM API 호출
    ↓
S3 저장 (notam-korea-data)
    ↓
S3 백업 (notam-backup)
```

## 📦 생성된 파일

1. **lambda_notam_crawler.py** - Lambda 함수 코드
2. **deploy_lambda.py** - 자동 배포 스크립트
3. **LAMBDA_SETUP_GUIDE.md** - 이 가이드

## 🚀 빠른 시작 (자동 배포)

### 1단계: 배포 실행

```bash
py deploy_lambda.py
```

이 스크립트가 자동으로:
1. IAM 역할 생성
2. Lambda 함수 생성/업데이트
3. EventBridge 스케줄 설정 (매 시간)
4. 권한 설정

### 2단계: 확인

AWS Console에서:
1. Lambda > Functions > `notam-realtime-crawler`
2. "Test" 버튼으로 수동 실행
3. CloudWatch Logs에서 로그 확인

### 3단계: S3 확인

```
s3://notam-korea-data/notam_realtime/2024-12-01/notam_20241201_100000.json
```

## 🛠️ 수동 설정 (선택사항)

자동 배포 대신 수동으로 설정하려면:

### 1. IAM 역할 생성

AWS Console > IAM > Roles > Create role

1. **Trusted entity**: Lambda
2. **Permissions**:
   - AWSLambdaBasicExecutionRole
   - AmazonS3FullAccess
3. **Role name**: `notam-lambda-role`

### 2. Lambda 함수 생성

AWS Console > Lambda > Create function

1. **Function name**: `notam-realtime-crawler`
2. **Runtime**: Python 3.11
3. **Role**: notam-lambda-role
4. **Code**: lambda_notam_crawler.py 내용 복사
5. **Handler**: lambda_function.lambda_handler
6. **Timeout**: 300초 (5분)
7. **Memory**: 512 MB

### 3. 환경 변수 설정

Lambda > Configuration > Environment variables

- `BUCKET_NAME`: notam-korea-data
- `BACKUP_BUCKET`: notam-backup

### 4. EventBridge 스케줄 설정

AWS Console > EventBridge > Rules > Create rule

1. **Name**: notam-crawler-schedule
2. **Schedule**: rate(1 hour)  # 매 시간
3. **Target**: Lambda function > notam-realtime-crawler

## ⏰ 스케줄 옵션

EventBridge 스케줄 표현식:

```python
# 매 시간
'rate(1 hour)'

# 매 30분
'rate(30 minutes)'

# 매일 오전 9시 (KST = UTC+9, 즉 UTC 0시)
'cron(0 0 * * ? *)'

# 매일 오전 9시, 오후 6시
'cron(0 0,9 * * ? *)'

# 평일 오전 9시
'cron(0 0 ? * MON-FRI *)'
```

스케줄 변경:
1. EventBridge > Rules > notam-crawler-schedule
2. Edit
3. Schedule expression 수정

## 📊 Lambda 함수 동작

### 수집 범위
- 오늘 날짜 NOTAM
- 국내(D) + 국제(I)
- 모든 공항
- 모든 시리즈 (A, C, D, E, G, Z, SNOWTAM)

### 저장 형식
```json
[
  {
    "notam_number": "A1234/24",
    "location": "RKSI",
    "series": "A",
    "qcode": "QMXLC",
    "qcode_mean": "Taxiway / Closed",
    "issue_time": "2412011000",
    "effective_start": "2412011200",
    "effective_end": "2412011400",
    "e_text": "TWY A CLOSED DUE TO MAINT",
    "full_text": "GG RKZZNAXX\n...",
    "fir": "RKRR",
    "ais_type": "A",
    "crawl_date": "2024-12-01",
    "crawl_timestamp": "2024-12-01T10:00:00",
    "data_source": "D"
  }
]
```

### S3 저장 경로
```
notam-korea-data/
  notam_realtime/
    2024-12-01/
      notam_20241201_100000.json
      notam_20241201_110000.json
      notam_20241201_120000.json
      ...
    2024-12-02/
      notam_20241202_000000.json
      ...
```

## 🔍 모니터링

### CloudWatch Logs
Lambda > Monitor > View logs in CloudWatch

로그 확인:
```
Starting NOTAM crawl at 2024-12-01T10:00:00
Saved 150 NOTAMs to s3://notam-korea-data/notam_realtime/2024-12-01/notam_20241201_100000.json
```

### CloudWatch Metrics
- Invocations (실행 횟수)
- Duration (실행 시간)
- Errors (오류 발생)
- Throttles (제한)

### 알람 설정 (선택사항)
CloudWatch > Alarms > Create alarm

- 메트릭: Lambda > Errors
- 조건: Errors > 1
- 알림: SNS 토픽으로 이메일 전송

## 💰 비용 추정

Lambda 프리 티어 (매월):
- 요청 1백만 건
- 컴퓨팅 400,000 GB-초

예상 사용량 (매 시간 실행):
- 요청: 720건/월 (24시간 × 30일)
- 실행 시간: ~10초/회
- 메모리: 512 MB
- **비용: $0 (프리 티어 범위 내)**

S3 비용:
- 스토리지: ~1GB/년
- 비용: ~$0.025/월

**총 예상 비용: 무료 ~ $0.03/월**

## 🔧 문제 해결

### Lambda 실행 실패
1. CloudWatch Logs 확인
2. IAM 역할 권한 확인
3. Timeout 증가 (Configuration > General > Timeout)

### S3 업로드 실패
```
An error occurred (AccessDenied)
```
→ IAM 역할에 S3 권한 추가

### 의존성 오류
```
No module named 'requests'
```
→ Lambda Layer 추가 필요 (아래 참조)

## 📦 requests 라이브러리 추가

Lambda는 기본적으로 `requests`가 없으므로 Layer 추가 필요:

### 방법 1: 공개 Layer 사용
1. Lambda > Configuration > Layers
2. Add a layer > Specify an ARN
3. ARN 입력:
   ```
   arn:aws:lambda:ap-northeast-2:770693421928:layer:Klayers-p311-requests:1
   ```

### 방법 2: 직접 Layer 생성
```bash
# 로컬에서 실행
mkdir python
pip install requests -t python/
zip -r requests-layer.zip python/

# AWS CLI로 업로드
aws lambda publish-layer-version \
  --layer-name requests \
  --zip-file fileb://requests-layer.zip \
  --compatible-runtimes python3.11
```

## 🔄 업데이트

코드 변경 후:
```bash
py deploy_lambda.py
```

또는 AWS Console에서:
1. Lambda > Code
2. 코드 수정
3. Deploy

## 🛑 중지/삭제

### 스케줄만 중지
EventBridge > Rules > notam-crawler-schedule > Disable

### 완전 삭제
```bash
# Lambda 함수 삭제
aws lambda delete-function --function-name notam-realtime-crawler

# IAM 역할 삭제
aws iam detach-role-policy --role-name notam-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam detach-role-policy --role-name notam-lambda-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam delete-role --role-name notam-lambda-role

# EventBridge 규칙 삭제
aws events remove-targets --rule notam-crawler-schedule --ids 1
aws events delete-rule --name notam-crawler-schedule
```

## 📈 고급 설정

### 병렬 처리
여러 Lambda 함수로 분산:
- Lambda 1: 국내 NOTAM
- Lambda 2: 국제 NOTAM

### 데이터 집계
매일 자정에 실행되는 별도 Lambda로 일일 요약 생성

### 알림
새 NOTAM 발견 시 SNS/이메일 알림

### API Gateway 연결
REST API로 실시간 NOTAM 조회 서비스 제공

## ✅ 체크리스트

- [ ] AWS 자격 증명 설정 완료
- [ ] boto3 설치 완료
- [ ] S3 버킷 생성 완료
- [ ] `py deploy_lambda.py` 실행
- [ ] Lambda 함수 테스트 성공
- [ ] CloudWatch Logs 확인
- [ ] S3에 데이터 저장 확인
- [ ] EventBridge 스케줄 확인

## 🎓 다음 단계

1. 매일 S3 데이터 확인
2. CloudWatch 모니터링 설정
3. 필요시 스케줄 조정
4. 데이터 분석 파이프라인 구축

## 📞 참고 자료

- AWS Lambda: https://docs.aws.amazon.com/lambda/
- EventBridge: https://docs.aws.amazon.com/eventbridge/
- boto3: https://boto3.amazonaws.com/v1/documentation/api/latest/
