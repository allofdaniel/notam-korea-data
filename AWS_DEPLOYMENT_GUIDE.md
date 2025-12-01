# AWS NOTAM 모니터링 시스템 배포 가이드 (비전문가용)

**작성일**: 2025-11-11
**난이도**: 초급~중급
**예상 소요시간**: 2-3시간
**예상 월 비용**: $5-15 (프리티어 제외 시)

---

## 📋 목차

1. [시스템 아키텍처 이해하기](#1-시스템-아키텍처-이해하기)
2. [필요한 AWS 서비스](#2-필요한-aws-서비스)
3. [배포 준비](#3-배포-준비)
4. [단계별 배포 가이드](#4-단계별-배포-가이드)
5. [테스트 및 모니터링](#5-테스트-및-모니터링)
6. [문제 해결](#6-문제-해결)
7. [비용 관리](#7-비용-관리)

---

## 1. 시스템 아키텍처 이해하기

### 🏗️ 전체 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS 클라우드                              │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  EventBridge (CloudWatch Events)                 │      │
│  │  매 1분마다 Lambda 함수 트리거                    │      │
│  └────────────────┬─────────────────────────────────┘      │
│                   │ 1분마다                                 │
│                   ▼                                         │
│  ┌────────────────────────────────────────────────┐        │
│  │  Lambda 함수 #1: NOTAM 크롤러                  │        │
│  │  - notam_crawler_api.py 실행                   │        │
│  │  - AIM 포털에서 데이터 수집                     │        │
│  │  - 실행시간: 0.2초 (초고속)                     │        │
│  └────┬────────────────────────────┬───────────────┘        │
│       │                            │                        │
│       │ 저장                       │ 백업                   │
│       ▼                            ▼                        │
│  ┌─────────────┐             ┌──────────────┐             │
│  │  DynamoDB   │             │     S3       │             │
│  │  테이블들:   │             │  - 일별 백업  │             │
│  │  - NOTAMs   │             │  - JSON 저장 │             │
│  │  - CrawlLog │             │  - 이력 보관 │             │
│  │  - Changes  │             └──────────────┘             │
│  └──────┬──────┘                                           │
│         │                                                  │
│         │ 조회                                             │
│         ▼                                                  │
│  ┌────────────────────────────────────────┐               │
│  │  Lambda 함수 #2, #3, #4: API 핸들러    │               │
│  │  - GET /api/notams (목록 조회)         │               │
│  │  - GET /api/notams/{id} (상세 조회)    │               │
│  │  - GET /api/stats (통계)               │               │
│  └────────────────┬───────────────────────┘               │
│                   ▲                                        │
│                   │                                        │
│  ┌────────────────┴───────────────────────┐               │
│  │  API Gateway                            │               │
│  │  https://xxxxx.execute-api.ap-northeast-2...│          │
│  └─────────────────────────────────────────┘               │
└──────────────────────┬─────────────────────────────────────┘
                       │ HTTPS
                       │
                  ┌────┴────┐
                  │  사용자  │
                  │ (브라우저,│
                  │  앱 등)  │
                  └─────────┘
```

### 🎯 각 서비스의 역할

1. **Lambda (서버리스 함수)**
   - 크롤러 Python 코드 실행
   - API 요청 처리
   - 서버 관리 불필요, 실행된 시간만큼만 과금

2. **EventBridge (스케줄러)**
   - 1분마다 Lambda 크롤러 자동 실행
   - Cron 표현식 사용 (예: `rate(1 minute)`)

3. **DynamoDB (NoSQL 데이터베이스)**
   - NOTAM 데이터 저장
   - 빠른 조회 속도
   - 자동 확장

4. **S3 (파일 저장소)**
   - 일별 백업 저장
   - JSON 파일로 전체 데이터 보관
   - 저렴한 장기 보관

5. **API Gateway (REST API)**
   - 외부에서 데이터 조회 가능한 엔드포인트 제공
   - HTTPS 자동 지원
   - 인증/권한 관리

---

## 2. 필요한 AWS 서비스

### ✅ 이미 활성화됨
- AWS 계정 ✓
- API Gateway ✓
- DynamoDB ✓
- S3 ✓

### 🆕 추가로 필요한 서비스
- **Lambda** (서버리스 함수)
- **EventBridge** (스케줄러)
- **IAM** (권한 관리) - 기본 제공됨
- **CloudWatch Logs** (로그 확인) - 기본 제공됨

---

## 3. 배포 준비

### 📦 로컬에서 준비할 파일들

현재 프로젝트에서 필요한 파일:
```
C:\Users\allof\Desktop\code\
├── lambda_crawler.py          ← 생성 필요 (Lambda용 크롤러)
├── lambda_api_handler.py      ← 생성 필요 (API 핸들러)
├── requirements.txt           ← 생성 필요 (패키지 목록)
├── notam_crawler_api.py       ← 기존 파일 활용
└── deployment/                ← 배포 폴더
    ├── lambda_package.zip     ← Lambda 업로드용
    └── deploy.sh              ← 자동 배포 스크립트
```

### 🔧 AWS CLI 설치 (선택사항)

**Windows PowerShell**:
```powershell
# AWS CLI 설치 (자동 배포 시 필요)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# 설치 확인
aws --version
```

**설정**:
```bash
aws configure
# AWS Access Key ID: (입력)
# AWS Secret Access Key: (입력)
# Default region name: ap-northeast-2  (서울 리전)
# Default output format: json
```

💡 **AWS CLI 없이도 배포 가능**: AWS 콘솔 웹 UI로 수동 배포 가능

---

## 4. 단계별 배포 가이드

### 📍 STEP 1: DynamoDB 테이블 생성 (5분)

#### 1.1 AWS 콘솔 접속
1. https://console.aws.amazon.com 접속
2. 로그인
3. 상단 검색에서 "DynamoDB" 검색
4. 리전이 **ap-northeast-2 (서울)** 인지 확인

#### 1.2 테이블 생성

**테이블 1: NOTAM_Records**
```
테이블 이름: NOTAM_Records
파티션 키: notam_id (String)
정렬 키: location (String)

설정:
- 테이블 클래스: 표준
- 읽기/쓰기 용량: 온디맨드
- 암호화: AWS 소유 키 사용
```

**테이블 2: NOTAM_CrawlLogs**
```
테이블 이름: NOTAM_CrawlLogs
파티션 키: log_id (String)
정렬 키: timestamp (Number)

설정:
- 읽기/쓰기 용량: 온디맨드
```

**테이블 3: NOTAM_Changes**
```
테이블 이름: NOTAM_Changes
파티션 키: change_id (String)
정렬 키: timestamp (Number)

설정:
- 읽기/쓰기 용량: 온디맨드
```

#### 1.3 GSI (Global Secondary Index) 생성

**NOTAM_Records 테이블에 인덱스 추가**:
```
인덱스 이름: data_source-issue_time-index
파티션 키: data_source (String)
정렬 키: issue_time (Number)
프로젝션: 모든 속성
```

---

### 📍 STEP 2: S3 버킷 생성 (3분)

#### 2.1 버킷 생성
```
버킷 이름: notam-backup-YYYYMMDD-UNIQUE
   예) notam-backup-20251111-abc123
리전: ap-northeast-2 (서울)
퍼블릭 액세스 차단: 모두 차단 (기본값)
버킷 버전 관리: 비활성화
암호화: SSE-S3 (기본값)
```

#### 2.2 폴더 구조 생성 (자동)
Lambda가 자동으로 생성합니다:
```
notam-backup-xxx/
├── daily/
│   ├── 2025-11-11/
│   │   ├── domestic.json
│   │   └── international.json
│   └── 2025-11-12/
├── monthly/
└── logs/
```

---

### 📍 STEP 3: Lambda 함수 생성 - 크롤러 (15분)

#### 3.1 Lambda 함수용 코드 작성

**파일: `lambda_crawler.py`** (이 파일을 생성해야 합니다)

#### 3.2 Lambda 레이어 생성 (Python 패키지)

Lambda에서는 외부 패키지를 "레이어"로 추가해야 합니다.

**로컬에서 패키지 준비**:
```bash
cd C:\Users\allof\Desktop\code
mkdir python
pip install requests pytz -t python/
zip -r lambda_layer.zip python/
```

**AWS Lambda 콘솔에서**:
1. Lambda → 레이어 → 레이어 생성
2. 이름: `notam-dependencies`
3. ZIP 파일 업로드: `lambda_layer.zip`
4. 런타임: Python 3.11

#### 3.3 Lambda 함수 생성

**기본 설정**:
```
함수 이름: notam-crawler
런타임: Python 3.11
아키텍처: x86_64

실행 역할: 새 역할 생성 (기본값)
   역할 이름: notam-crawler-role (자동 생성)
```

**고급 설정**:
```
메모리: 256 MB
타임아웃: 2분 (120초)
환경 변수:
   - DYNAMODB_TABLE_NOTAMS: NOTAM_Records
   - DYNAMODB_TABLE_LOGS: NOTAM_CrawlLogs
   - DYNAMODB_TABLE_CHANGES: NOTAM_Changes
   - S3_BUCKET_NAME: notam-backup-xxx
   - AWS_REGION: ap-northeast-2
```

#### 3.4 코드 업로드

**방법 1: 직접 붙여넣기** (작은 파일)
- Lambda 콘솔에서 코드 에디터에 직접 붙여넣기

**방법 2: ZIP 업로드** (권장)
```bash
# 로컬에서
cd C:\Users\allof\Desktop\code
zip -r lambda_crawler.zip lambda_crawler.py notam_crawler_api.py

# AWS Lambda 콘솔에서
# "Upload from" → ".zip file" → lambda_crawler.zip 선택
```

#### 3.5 레이어 연결
1. Lambda 함수 → 구성 → 레이어
2. "레이어 추가" 클릭
3. "사용자 지정 레이어" 선택
4. `notam-dependencies` 선택
5. 저장

#### 3.6 IAM 권한 추가

Lambda 함수가 DynamoDB와 S3에 접근하려면 권한이 필요합니다.

1. Lambda 함수 → 구성 → 권한
2. 실행 역할 이름 클릭 (IAM 콘솔로 이동)
3. "권한 추가" → "정책 연결"
4. 다음 정책들 추가:
   - `AmazonDynamoDBFullAccess`
   - `AmazonS3FullAccess`
   - `CloudWatchLogsFullAccess` (기본 포함)

---

### 📍 STEP 4: EventBridge 스케줄러 설정 (5분)

#### 4.1 EventBridge 규칙 생성

1. AWS 콘솔 → EventBridge → 규칙
2. "규칙 생성" 클릭

**기본 세부 정보**:
```
이름: notam-crawler-schedule
설명: NOTAM 크롤러 1분마다 실행
이벤트 버스: default
규칙 유형: 일정
```

**일정 정의**:
```
일정 패턴: 속도 기반 일정
속도: rate(1 minute)

또는 Cron 표현식:
cron(* * * * ? *)
```

**대상 선택**:
```
대상 유형: AWS 서비스
대상 선택: Lambda 함수
함수: notam-crawler
```

**재시도 정책**:
```
최대 재시도 횟수: 2
최대 이벤트 기간: 1시간
```

3. "규칙 생성" 클릭

---

### 📍 STEP 5: Lambda 함수 생성 - API 핸들러 (10분)

API Gateway에서 호출할 Lambda 함수들을 생성합니다.

#### 5.1 Lambda 함수: GET /api/notams

**함수 이름**: `notam-api-list`
**런타임**: Python 3.11
**메모리**: 256 MB
**타임아웃**: 30초

**코드**: `lambda_api_handler.py` (나중에 제공)

#### 5.2 Lambda 함수: GET /api/notams/{id}

**함수 이름**: `notam-api-get`
**런타임**: Python 3.11

#### 5.3 Lambda 함수: GET /api/stats

**함수 이름**: `notam-api-stats`
**런타임**: Python 3.11

#### 5.4 권한 설정

모든 API Lambda 함수에 DynamoDB 읽기 권한 부여:
- `AmazonDynamoDBReadOnlyAccess`

---

### 📍 STEP 6: API Gateway 설정 (15분)

#### 6.1 REST API 생성

1. AWS 콘솔 → API Gateway
2. "REST API" → "빌드" 클릭

**API 설정**:
```
프로토콜: REST
새 API 생성: 새 API
API 이름: notam-api
설명: NOTAM 데이터 조회 API
엔드포인트 유형: 지역
```

#### 6.2 리소스 및 메서드 생성

**리소스 구조**:
```
/
├── /api
    ├── /notams
    │   ├── GET (목록 조회)
    │   └── /{id}
    │       └── GET (상세 조회)
    ├── /stats
    │   └── GET (통계)
    └── /crawl
        └── POST (수동 트리거)
```

**생성 방법**:

1. `/api` 리소스 생성
   - "작업" → "리소스 생성"
   - 리소스 이름: api
   - 리소스 경로: /api

2. `/api/notams` 리소스 생성
   - `/api` 선택 → "작업" → "리소스 생성"
   - 리소스 이름: notams
   - CORS 활성화: ✓

3. `GET /api/notams` 메서드 생성
   - `/api/notams` 선택 → "작업" → "메서드 생성"
   - GET 선택
   - 통합 유형: Lambda 함수
   - Lambda 함수: `notam-api-list`
   - 저장

4. `/{id}` 리소스 생성
   - `/api/notams` 선택 → "작업" → "리소스 생성"
   - 리소스 이름: {id}
   - 리소스 경로: /{id}

5. `GET /api/notams/{id}` 메서드 생성
   - `/{id}` 선택 → GET 메서드
   - Lambda 함수: `notam-api-get`

6. 나머지 리소스/메서드도 동일하게 생성

#### 6.3 CORS 설정

모든 메서드에 CORS 활성화:
1. 메서드 선택 → "작업" → "CORS 활성화"
2. 기본값으로 저장

#### 6.4 API 배포

1. "작업" → "API 배포"
2. 배포 스테이지: [새 스테이지]
3. 스테이지 이름: `prod`
4. 배포

**API URL 확인**:
```
https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod
```

---

## 5. 테스트 및 모니터링

### 🧪 테스트

#### 5.1 Lambda 크롤러 테스트

1. Lambda 콘솔 → `notam-crawler` 함수
2. "테스트" 탭 → 테스트 이벤트 생성
3. 빈 JSON `{}` 입력
4. "테스트" 실행

**성공 시 응답**:
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

#### 5.2 API 테스트

**브라우저 또는 curl**:
```bash
# NOTAM 목록 조회
curl https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod/api/notams?data_source=domestic

# 통계 조회
curl https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod/api/stats
```

### 📊 모니터링

#### CloudWatch Logs 확인

1. CloudWatch → 로그 그룹
2. `/aws/lambda/notam-crawler` 선택
3. 최신 로그 스트림 확인

**정상 로그 예시**:
```
[INFO] NOTAM 크롤러 시작
[INFO] 국내 NOTAM: 8개 발견
[INFO] 국제 NOTAM: 7개 발견
[INFO] S3 백업 완료
```

#### CloudWatch 메트릭

1. CloudWatch → 메트릭
2. Lambda → 함수별 메트릭
3. 확인할 항목:
   - Invocations (호출 횟수)
   - Duration (실행 시간)
   - Errors (오류)
   - Throttles (제한)

---

## 6. 문제 해결

### ❌ 일반적인 문제

#### 문제 1: Lambda 타임아웃
```
오류: Task timed out after 3.00 seconds
```
**해결**: Lambda 타임아웃 늘리기 (구성 → 제한 시간: 120초)

#### 문제 2: DynamoDB 권한 오류
```
오류: AccessDeniedException
```
**해결**: IAM 역할에 DynamoDB 권한 추가

#### 문제 3: 패키지 import 오류
```
오류: No module named 'requests'
```
**해결**: Lambda 레이어 확인 및 재생성

#### 문제 4: API Gateway CORS 오류
```
오류: No 'Access-Control-Allow-Origin' header
```
**해결**: CORS 활성화 및 API 재배포

---

## 7. 비용 관리

### 💰 예상 월 비용 (서울 리전 기준)

#### 프리티어 (12개월 무료)
- Lambda: 월 100만 건 요청, 40만 GB-초 무료
- DynamoDB: 월 25 GB 저장, 25 WCU, 25 RCU 무료
- S3: 월 5 GB 저장, 20,000 GET, 2,000 PUT 무료
- API Gateway: 월 100만 API 호출 무료

#### 프리티어 초과 시 예상 비용

**Lambda (크롤러 1분마다)**:
- 호출 횟수: 43,200회/월 (1분 × 60 × 24 × 30)
- 실행 시간: 0.2초 × 43,200 = 8,640초 = 2.4 GB-초
- **비용**: 프리티어로 충분 → $0

**DynamoDB**:
- 온디맨드 모드
- 쓰기: 43,200회/월 × 2건 = 86,400 WRU
- 읽기: 1,000회/월 = 1,000 RRU
- **비용**: 약 $1-2/월

**S3**:
- 저장: 1 GB/월
- PUT: 1,440회/월 (1분마다 백업)
- **비용**: 약 $0.03/월

**API Gateway**:
- API 호출: 10,000회/월 (예상)
- **비용**: 프리티어로 충분 → $0

**총 예상 비용**: **$1-3/월** (프리티어 이후)

### 💡 비용 절감 팁

1. **크롤링 주기 늘리기**: 1분 → 5분 (비용 80% 절감)
2. **S3 백업 주기 늘리기**: 1분마다 → 1시간마다
3. **DynamoDB 프로비저닝 모드**: 온디맨드 → 프로비저닝 (일정한 트래픽 시)
4. **CloudWatch Logs 보존 기간**: 무기한 → 7일

---

## 8. 다음 단계

배포 후 개선 사항:
1. ✅ CloudWatch 알람 설정 (크롤링 실패 시 이메일)
2. ✅ API 인증 추가 (API 키 또는 Cognito)
3. ✅ 웹 대시보드 구축 (React + Amplify)
4. ✅ 변경 감지 알림 (SNS + 이메일/SMS)

---

## 📞 추가 지원

- AWS 프리티어: https://aws.amazon.com/free/
- Lambda 문서: https://docs.aws.amazon.com/lambda/
- DynamoDB 문서: https://docs.aws.amazon.com/dynamodb/
- API Gateway 문서: https://docs.aws.amazon.com/apigateway/

---

**다음 파일에서 실제 코드를 제공합니다**:
- `lambda_crawler.py` - Lambda용 크롤러 코드
- `lambda_api_handler.py` - API 핸들러 코드
- `deploy.sh` - 자동 배포 스크립트
