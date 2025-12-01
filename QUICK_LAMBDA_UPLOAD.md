# Lambda 완전 NOTAM API - 빠른 업로드 가이드

## 상황
- Lambda 함수 코드 준비 완료 ✓
- 배포 패키지 생성 완료 ✓ (lambda_notam_query_complete.zip - 392 KB)
- IAM 권한 부족으로 자동 배포 불가

## 가장 빠른 배포 방법 (5분)

### 1단계: AWS Lambda Console 접속

https://ap-southeast-2.console.aws.amazon.com/lambda/home?region=ap-southeast-2#/functions

### 2단계: 함수 생성

**Create function** 클릭 후:
- **Function name**: `notam-query-complete`
- **Runtime**: Python 3.11
- **Architecture**: x86_64
- **Permissions** → Change default execution role:
  - Use an existing role: `notam-lambda-role`
- **Create function** 클릭

### 3단계: 코드 업로드

1. **Code** 탭에서 **Upload from** → **.zip file** 클릭
2. **Upload** 버튼 클릭 → `lambda_notam_query_complete.zip` 선택
3. **Save** 클릭

### 4단계: 환경 설정

**Configuration** 탭:

#### General configuration → Edit:
- **Timeout**: 300 초 (5분)
- **Memory**: 512 MB
- **Save**

#### Environment variables → Edit → Add:
- Key: `BUCKET_NAME`
- Value: `notam-korea-data`
- **Save**

### 5단계: API Gateway 연결

**기존 API Gateway (notam-api)에 엔드포인트 추가**:

https://ap-southeast-2.console.aws.amazon.com/apigateway/main/apis/k9cp26l1ra/resources?api=k9cp26l1ra&region=ap-southeast-2

#### 방법 1: 자동 연결 (권장)
Lambda 함수 페이지에서:
1. **Add trigger** 클릭
2. **API Gateway** 선택
3. API: `notam-api`
4. Deployment stage: `prod`
5. Security: Open
6. **Add**

#### 방법 2: 수동 연결 (세밀한 제어)
API Gateway Console에서:
1. `/notams` 리소스 선택
2. **Actions** → **Create Resource**:
   - Resource Name: `stats`
   - Enable CORS: ✓
3. **Actions** → **Create Method** → GET:
   - Integration type: Lambda Function
   - Lambda Proxy integration: ✓
   - Lambda Function: `notam-query-complete`
   - Save
4. 반복: `active`, `expired`, `trigger`, `complete` 엔드포인트도 생성
5. **Actions** → **Deploy API** → Stage: `prod`

### 6단계: 테스트

```bash
# 통계 조회
curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/stats"

# 특정 날짜 통계
curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/stats?date=2024-12-01"

# 활성 NOTAM
curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/active"

# 만료 NOTAM
curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/expired"

# 트리거 NOTAM
curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/trigger"
```

## 예상 응답

### /stats
```json
{
  "total": 154986,
  "active": 2145,
  "expired": 152341,
  "trigger": 500,
  "scheduled": 0,
  "filter_date": null,
  "current_time": "2025-12-01T15:30:45.123456"
}
```

### /stats?date=2024-12-01
```json
{
  "total": 111,
  "active": 14,
  "expired": 92,
  "trigger": 5,
  "scheduled": 0,
  "filter_date": "2024-12-01",
  "current_time": "2025-12-01T15:30:45.123456"
}
```

### /active
```json
{
  "stats": {
    "total": 154986,
    "active": 2145,
    ...
  },
  "data": [
    {
      "notam_number": "A1234/25",
      "location": "RKSI",
      "status": "active",
      "effective_start": "2501011200",
      "effective_end": "2503312359",
      "q_code": "QMXLC",
      "e_text": "RWY 15L/33R CLSD FOR MAINTENANCE",
      ...
    }
  ]
}
```

## 로컬 테스트 (배포 전)

```bash
# 테스트 실행
py lambda_notam_query_complete.py

# 예상 출력: 2024-12-01 통계
{
  "total": 111,
  "active": 14,
  "expired": 92,
  "trigger": 5,
  "scheduled": 0,
  "filter_date": "2024-12-01",
  "current_time": "..."
}
```

## 문제 해결

### "Unable to import module 'lambda_function'"
- ZIP 파일이 손상되었을 수 있음
- `lambda_notam_query_complete.zip` 다시 업로드

### "S3 access denied"
- `notam-lambda-role`에 S3 읽기 권한 확인
- IAM Role → Permissions → `AmazonS3ReadOnlyAccess` 필요

### "Task timed out after 3.00 seconds"
- Configuration → General → Timeout을 300초로 증가

### API Gateway 404 Error
- API Gateway에서 **Deploy API** 했는지 확인
- Stage: `prod` 선택

## 다음 단계

1. ✅ Lambda 함수 배포
2. ✅ API Gateway 엔드포인트 추가
3. ⬜ NOTAM 앱에 새 API 통합:
   - `src/services/notamApi.js`에 메서드 추가
   - 날짜 선택 UI 추가
   - 상태별 필터 버튼 추가

## 참고 문서
- 상세 가이드: `DEPLOY_COMPLETE_NOTAM_API.md`
- Lambda 함수 코드: `lambda_notam_query_complete.py`
- 배포 패키지: `lambda_notam_query_complete.zip`
