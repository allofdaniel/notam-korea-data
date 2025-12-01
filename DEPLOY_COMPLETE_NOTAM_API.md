# Lambda 완전 NOTAM API 배포 가이드

## 🎯 기능

S3의 154,986개 전체 NOTAM 데이터 조회
- 날짜별 필터링
- 상태별 분류 (활성/만료/트리거/예정)
- 통계 제공

## 📦 1단계: Lambda 함수 생성

### AWS Console 접속
https://ap-southeast-2.console.aws.amazon.com/lambda

### 함수 생성
1. **Create function** 클릭
2. 설정:
   - **Function name**: `notam-query-complete`
   - **Runtime**: Python 3.11
   - **Architecture**: x86_64
   - **Permissions**: Use an existing role → `notam-lambda-role`
3. **Create function** 클릭

## 📝 2단계: 코드 업로드

### 코드 복사

`lambda_notam_query_complete.py` 파일 내용을 복사하여 Lambda 함수 코드 에디터에 붙여넣기

**주의**: `lambda_function.py`로 이름 변경 필요

### 환경 변수 설정

Configuration → Environment variables → Edit:
```
BUCKET_NAME = notam-korea-data
```

### 설정 변경

Configuration → General configuration → Edit:
- **Timeout**: 30초 (300초로 증가 권장)
- **Memory**: 512 MB (또는 1024 MB)

## 🔗 3단계: API Gateway 엔드포인트 추가

### 기존 API Gateway에 리소스 추가

1. **API Gateway Console** 접속
2. `notam-api` 선택 (기존 API)
3. **Resources** 탭

### 새 리소스 생성

#### `/notams/complete` 엔드포인트
1. Actions → Create Resource
   - Resource Name: `complete`
   - Resource Path: `/complete`
   - Enable CORS: ✓

2. Actions → Create Method → GET
   - Integration type: Lambda Function
   - Use Lambda Proxy integration: ✓
   - Lambda Function: `notam-query-complete`
   - Save

#### `/notams/stats` 엔드포인트
1. Actions → Create Resource
   - Resource Name: `stats`
   - Resource Path: `/stats`
   - Enable CORS: ✓

2. Actions → Create Method → GET
   - Integration type: Lambda Function
   - Use Lambda Proxy integration: ✓
   - Lambda Function: `notam-query-complete`
   - Save

#### `/notams/active` 엔드포인트
(위와 동일하게 반복)

#### `/notams/expired` 엔드포인트
(위와 동일하게 반복)

#### `/notams/trigger` 엔드포인트
(위와 동일하게 반복)

#### `/notams/date/{date}` 엔드포인트
1. Actions → Create Resource
   - Resource Name: `date`
   - Resource Path: `/date`

2. `/date` 리소스 선택 → Actions → Create Resource
   - Resource Name: `date`
   - Resource Path: `/{date}`
   - Enable CORS: ✓

3. Actions → Create Method → GET
   - Integration type: Lambda Function
   - Use Lambda Proxy integration: ✓
   - Lambda Function: `notam-query-complete`
   - Save

## 🚀 4단계: API 배포

1. Actions → Deploy API
2. Deployment stage: `prod`
3. Deploy

## ✅ 5단계: 테스트

### API URL
```
https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod
```

### 테스트 엔드포인트

```bash
# 전체 통계
curl https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/stats

# 특정 날짜 통계
curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/stats?date=2024-12-01"

# 현재 활성 NOTAM
curl https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/active

# 만료된 NOTAM
curl https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/expired

# 트리거 NOTAM
curl https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/trigger

# 전체 NOTAM (분류됨, 제한 100개)
curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/complete?limit=100"

# 특정 날짜 NOTAM
curl https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/date/2024-12-01
```

## 📊 응답 예시

### `/notams/stats?date=2024-12-01`
```json
{
  "total": 111,
  "active": 14,
  "expired": 92,
  "trigger": 5,
  "scheduled": 0,
  "filter_date": "2024-12-01",
  "current_time": "2025-12-01T15:00:45.342578"
}
```

### `/notams/active`
```json
{
  "stats": {
    "total": 154986,
    "active": 2145,
    "expired": 152341,
    "trigger": 500,
    "scheduled": 0
  },
  "data": [
    {
      "notam_number": "A1234/25",
      "location": "RKSI",
      "status": "active",
      ...
    }
  ]
}
```

## 🎨 앱 통합

### NOTAM 앱에서 사용

`src/services/notamApi.js`에 추가:

```javascript
/**
 * 전체 NOTAM 통계
 */
async getNotamStats(date = null) {
  try {
    const url = date ? `/notams/stats?date=${date}` : '/notams/stats';
    const response = await this.client.get(url);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error,
    };
  }
}

/**
 * 활성 NOTAM만 가져오기
 */
async getActiveNotams(date = null) {
  try {
    const url = date ? `/notams/active?date=${date}` : '/notams/active';
    const response = await this.client.get(url);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error,
    };
  }
}

/**
 * 만료된 NOTAM
 */
async getExpiredNotams(date = null) {
  try {
    const url = date ? `/notams/expired?date=${date}` : '/notams/expired';
    const response = await this.client.get(url);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error,
    };
  }
}

/**
 * 트리거 NOTAM
 */
async getTriggerNotams(date = null) {
  try {
    const url = date ? `/notams/trigger?date=${date}` : '/notams/trigger';
    const response = await this.client.get(url);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error,
    };
  }
}

/**
 * 특정 날짜 NOTAM
 */
async getNotamsByDate(date) {
  try {
    const response = await this.client.get(`/notams/date/${date}`);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error,
    };
  }
}
```

## 🎯 다음 단계

1. Lambda 함수 테스트
2. API Gateway 엔드포인트 테스트
3. 앱에서 통합 테스트
4. 날짜 선택 UI 추가
5. NOTAM 상태별 필터 UI 추가

## 💡 UI 개선 아이디어

### 통계 카드
```
📊 NOTAM 통계 (2024-12-01)
━━━━━━━━━━━━━━━━━━━━━━━
전체: 154,986개
✅ 활성: 2,145개
❌ 만료: 152,341개
🔔 트리거: 500개
```

### 필터 버튼
```
[ 전체 ] [ 활성 ] [ 만료 ] [ 트리거 ]
```

### 날짜 선택기
```
📅 2024-12-01  [◀ 이전날] [다음날 ▶]
```
