# AWS 배포 빠른 시작 가이드 (비전문가용)

**소요 시간**: 30분~1시간
**난이도**: 초급
**비용**: 월 $1-3 (프리티어 이후)

---

## 🎯 이 가이드의 목표

1분마다 자동으로 NOTAM 데이터를 수집하고, REST API로 제공하는 시스템을 AWS에 배포합니다.

```
EventBridge (1분마다) → Lambda 크롤러 → DynamoDB + S3
                                           ↓
                          사용자 → API Gateway → Lambda API
```

---

## 📋 준비물 체크리스트

- [ ] AWS 계정 (있음 ✓)
- [ ] AWS CLI 설치 (선택사항)
- [ ] 로컬 파일:
  - [ ] `lambda_crawler.py`
  - [ ] `lambda_api_handlers.py`
  - [ ] `requirements.txt`
  - [ ] `deploy_to_aws.ps1`

---

## 🚀 단계별 가이드

### STEP 1: 배포 패키지 생성 (5분)

**Windows PowerShell에서**:
```powershell
cd C:\Users\allof\Desktop\code
.\deploy_to_aws.ps1
```

**생성되는 파일**:
- `deployment/layer/lambda_layer.zip` (3-5 MB) - Python 패키지
- `deployment/crawler/lambda_crawler.zip` (10 KB) - 크롤러 코드
- `deployment/api/lambda_api.zip` (8 KB) - API 핸들러 코드

---

### STEP 2: DynamoDB 테이블 생성 (5분)

#### 2.1 AWS 콘솔 접속
1. https://console.aws.amazon.com 접속 및 로그인
2. 우측 상단 리전: **ap-northeast-2 (서울)** 확인
3. 검색창에 "DynamoDB" 입력

#### 2.2 테이블 3개 생성

**클릭 경로**: DynamoDB → 테이블 → 테이블 생성

**테이블 1**:
```
테이블 이름: NOTAM_Records
파티션 키: notam_id (문자열)
정렬 키: location (문자열)
테이블 설정: 기본 설정
테이블 클래스: DynamoDB 표준
읽기/쓰기 용량 모드: 온디맨드

→ [테이블 생성] 클릭
```

**테이블 2**:
```
테이블 이름: NOTAM_CrawlLogs
파티션 키: log_id (문자열)
정렬 키: timestamp (숫자)
읽기/쓰기 용량 모드: 온디맨드

→ [테이블 생성] 클릭
```

**테이블 3**:
```
테이블 이름: NOTAM_Changes
파티션 키: change_id (문자열)
정렬 키: timestamp (숫자)
읽기/쓰기 용량 모드: 온디맨드

→ [테이블 생성] 클릭
```

#### 2.3 GSI (인덱스) 생성

1. `NOTAM_Records` 테이블 클릭
2. "인덱스" 탭 → "인덱스 생성"
3. 설정:
   ```
   인덱스 이름: data_source-issue_time-index
   파티션 키: data_source (문자열)
   정렬 키: issue_time (숫자)
   속성 프로젝션: 모두
   ```
4. [인덱스 생성] 클릭

---

### STEP 3: S3 버킷 생성 (3분)

1. 검색창에 "S3" 입력
2. "버킷 만들기" 클릭
3. 설정:
   ```
   버킷 이름: notam-backup-20251111-UNIQUE
      (UNIQUE는 아무 문자나 입력, 예: abc123)

   AWS 리전: 아시아 태평양(서울) ap-northeast-2

   객체 소유권: ACL 비활성화됨 (기본값)

   퍼블릭 액세스 차단: 모든 퍼블릭 액세스 차단 (기본값)

   버킷 버전 관리: 비활성화 (기본값)

   기본 암호화: 서버 측 암호화 - Amazon S3 관리형 키(SSE-S3)
   ```
4. [버킷 만들기] 클릭
5. **버킷 이름 메모해두기** (나중에 사용)

---

### STEP 4: Lambda 레이어 생성 (3분)

1. 검색창에 "Lambda" 입력
2. 좌측 메뉴 → "레이어" → "레이어 생성"
3. 설정:
   ```
   이름: notam-dependencies
   설명: NOTAM 크롤러 Python 패키지

   ".zip 파일 업로드" 선택
   → [업로드] → deployment/layer/lambda_layer.zip 선택

   호환 런타임: Python 3.11
   ```
4. [생성] 클릭

---

### STEP 5: Lambda 함수 생성 - 크롤러 (10분)

#### 5.1 함수 생성

1. Lambda → 함수 → "함수 생성"
2. 설정:
   ```
   작성 옵션: 새로 작성

   함수 이름: notam-crawler

   런타임: Python 3.11

   아키텍처: x86_64

   권한: 기본 Lambda 권한을 가진 새 역할 생성 (기본값)
   ```
3. [함수 생성] 클릭

#### 5.2 코드 업로드

1. "코드" 탭에서 → ".zip 파일 업로드"
2. `deployment/crawler/lambda_crawler.zip` 선택
3. [저장] 클릭

#### 5.3 레이어 추가

1. "코드" 탭 아래 → "레이어" 섹션 → "레이어 추가"
2. "사용자 지정 레이어" 선택
3. "notam-dependencies" 선택, 버전 1
4. [추가] 클릭

#### 5.4 환경 변수 설정

1. "구성" 탭 → "환경 변수" → "편집"
2. 다음 변수 추가:
   ```
   DYNAMODB_TABLE_NOTAMS = NOTAM_Records
   DYNAMODB_TABLE_LOGS = NOTAM_CrawlLogs
   DYNAMODB_TABLE_CHANGES = NOTAM_Changes
   S3_BUCKET_NAME = notam-backup-20251111-abc123  (본인 버킷 이름)
   AWS_REGION = ap-northeast-2
   ```
3. [저장] 클릭

#### 5.5 제한 시간 설정

1. "구성" 탭 → "일반 구성" → "편집"
2. 설정:
   ```
   메모리: 256 MB
   제한 시간: 2분 0초
   ```
3. [저장] 클릭

#### 5.6 IAM 권한 추가

1. "구성" 탭 → "권한" 탭
2. "역할 이름" 클릭 (새 탭에서 IAM 콘솔 열림)
3. "권한 추가" → "정책 연결"
4. 검색하여 다음 정책 체크:
   - `AmazonDynamoDBFullAccess` (DynamoDB 읽기/쓰기)
   - `AmazonS3FullAccess` (S3 읽기/쓰기)
5. [권한 추가] 클릭

---

### STEP 6: Lambda 테스트 (2분)

1. Lambda 함수 `notam-crawler` 페이지로 돌아가기
2. "테스트" 탭 → "테스트 이벤트 구성"
3. 이벤트 이름: `test`
4. 이벤트 JSON: `{}` (빈 객체)
5. [저장] 클릭
6. [테스트] 버튼 클릭

**성공 시 출력**:
```json
{
  "statusCode": 200,
  "body": {
    "status": "success",
    "domestic": {
      "records_found": 8,
      "records_saved": 8
    },
    "international": {
      "records_found": 7,
      "records_saved": 7
    }
  }
}
```

**실패 시**:
- CloudWatch Logs 확인 (함수 페이지 → "모니터" 탭 → "CloudWatch의 로그 보기")
- 환경 변수 재확인
- IAM 권한 재확인

---

### STEP 7: EventBridge 스케줄러 설정 (5분)

#### 7.1 EventBridge 규칙 생성

1. 검색창에 "EventBridge" 입력
2. 좌측 메뉴 → "규칙" → "규칙 생성"
3. 설정:
   ```
   이름: notam-crawler-schedule
   설명: NOTAM 크롤러 1분마다 실행

   이벤트 버스: default

   규칙 유형: 일정
   ```
4. [다음] 클릭

#### 7.2 일정 패턴 정의

```
일정 패턴: 속도 기반 일정

속도 표현식: rate(1 minute)
```

5. [다음] 클릭

#### 7.3 대상 선택

```
대상 유형: AWS 서비스

대상 선택: Lambda 함수

함수: notam-crawler
```

6. [다음] → [다음] → [규칙 생성] 클릭

**이제 1분마다 자동으로 크롤링됩니다!**

---

### STEP 8: API Gateway 설정 (15분)

#### 8.1 REST API 생성

1. 검색창에 "API Gateway" 입력
2. "API 생성" → "REST API" (프라이빗 아님) → "빌드"
3. 설정:
   ```
   프로토콜: REST

   새 API 생성: 새 API

   API 이름: notam-api
   설명: NOTAM 데이터 조회 API

   엔드포인트 유형: 지역
   ```
4. [API 생성] 클릭

#### 8.2 Lambda 함수 생성 (API용)

먼저 API 핸들러 Lambda 함수 3개를 만들어야 합니다.

**함수 1: notam-api-list**
```
함수 이름: notam-api-list
런타임: Python 3.11
코드: deployment/api/lambda_api.zip 업로드
핸들러: lambda_api_handlers.get_notams_list
레이어: notam-dependencies 추가
환경 변수:
  - DYNAMODB_TABLE_NOTAMS = NOTAM_Records
  - DYNAMODB_TABLE_LOGS = NOTAM_CrawlLogs
  - AWS_REGION = ap-northeast-2
권한: AmazonDynamoDBReadOnlyAccess
```

**함수 2: notam-api-stats**
```
함수 이름: notam-api-stats
런타임: Python 3.11
코드: deployment/api/lambda_api.zip 업로드
핸들러: lambda_api_handlers.get_statistics
레이어: notam-dependencies 추가
환경 변수: (함수 1과 동일)
권한: AmazonDynamoDBReadOnlyAccess
```

**함수 3: notam-api-crawl**
```
함수 이름: notam-api-crawl
런타임: Python 3.11
코드: deployment/api/lambda_api.zip 업로드
핸들러: lambda_api_handlers.trigger_manual_crawl
레이어: notam-dependencies 추가
환경 변수:
  - CRAWLER_LAMBDA_NAME = notam-crawler
  - AWS_REGION = ap-northeast-2
권한: AmazonDynamoDBReadOnlyAccess + AWSLambda_FullAccess
```

#### 8.3 API Gateway 리소스 및 메서드 생성

1. API Gateway → `notam-api` 선택

**리소스 /api 생성**:
1. "작업" → "리소스 생성"
2. 리소스 이름: `api`
3. 리소스 경로: `/api`
4. [리소스 생성] 클릭

**리소스 /api/notams 생성**:
1. `/api` 선택 → "작업" → "리소스 생성"
2. 리소스 이름: `notams`
3. CORS 활성화: ✓ 체크
4. [리소스 생성] 클릭

**메서드 GET /api/notams 생성**:
1. `/api/notams` 선택 → "작업" → "메서드 생성"
2. GET 선택 → ✓ 클릭
3. 설정:
   ```
   통합 유형: Lambda 함수
   Lambda 프록시 통합 사용: ✓ 체크
   Lambda 함수: notam-api-list
   ```
4. [저장] 클릭 → [확인] 클릭

**리소스 /api/stats 생성 및 메서드 추가**:
1. `/api` 선택 → "작업" → "리소스 생성"
2. 리소스 이름: `stats`
3. CORS 활성화: ✓
4. [리소스 생성] 클릭
5. `/api/stats` 선택 → GET 메서드 생성
6. Lambda 함수: `notam-api-stats`

**리소스 /api/crawl 생성 및 메서드 추가**:
1. `/api` 선택 → "작업" → "리소스 생성"
2. 리소스 이름: `crawl`
3. CORS 활성화: ✓
4. [리소스 생성] 클릭
5. `/api/crawl` 선택 → POST 메서드 생성
6. Lambda 함수: `notam-api-crawl`

#### 8.4 CORS 활성화

1. 각 리소스 (`/api/notams`, `/api/stats`, `/api/crawl`) 선택
2. "작업" → "CORS 활성화"
3. 기본값 유지 → [CORS 활성화 및 기존 CORS 헤더 바꾸기] 클릭
4. [예, 기존 값 바꾸기] 클릭

#### 8.5 API 배포

1. "작업" → "API 배포"
2. 배포 스테이지: [새 스테이지]
3. 스테이지 이름: `prod`
4. [배포] 클릭

**API URL 표시됨**:
```
https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod
```

**이 URL을 메모해두세요!**

---

### STEP 9: API 테스트 (3분)

브라우저 또는 curl로 테스트:

**1. NOTAM 목록 조회**:
```
https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod/api/notams?data_source=domestic&limit=10
```

**2. 통계 조회**:
```
https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod/api/stats
```

**3. 수동 크롤링 (curl)**:
```bash
curl -X POST https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod/api/crawl \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## ✅ 배포 완료!

축하합니다! 이제 다음이 자동으로 동작합니다:

1. ⏰ **1분마다 자동 크롤링** (EventBridge → Lambda)
2. 💾 **DynamoDB에 데이터 저장** (실시간 조회용)
3. 📦 **S3에 백업** (장기 보관용)
4. 🌐 **REST API 제공** (API Gateway)

---

## 📊 모니터링

### CloudWatch Logs 확인
1. CloudWatch → 로그 그룹
2. `/aws/lambda/notam-crawler` 선택
3. 최신 로그 스트림 확인

### CloudWatch 메트릭
1. CloudWatch → 메트릭 → Lambda
2. 함수별 메트릭:
   - Invocations (호출 횟수)
   - Duration (실행 시간)
   - Errors (오류)

---

## 💰 예상 비용

**프리티어 (12개월)**:
- Lambda: 월 100만 요청 무료
- DynamoDB: 25 GB, 25 WCU, 25 RCU 무료
- S3: 5 GB, 20,000 GET, 2,000 PUT 무료
- API Gateway: 월 100만 호출 무료

**프리티어 이후**:
- 월 $1-3 (정상 사용 시)

**비용 절감 팁**:
- 크롤링 주기: 1분 → 5분 (비용 80% 절감)
- S3 백업: 1분마다 → 1시간마다

---

## 🔧 문제 해결

### Lambda 타임아웃
→ Lambda 구성 → 제한 시간 늘리기 (120초)

### DynamoDB 권한 오류
→ IAM 역할에 DynamoDB 권한 추가

### API CORS 오류
→ API Gateway에서 CORS 재활성화 및 재배포

---

## 📞 도움이 필요하면

- AWS 프리티어: https://aws.amazon.com/free/
- Lambda 문서: https://docs.aws.amazon.com/lambda/
- 상세 가이드: `AWS_DEPLOYMENT_GUIDE.md`

---

**배포 완료! 🎉**
