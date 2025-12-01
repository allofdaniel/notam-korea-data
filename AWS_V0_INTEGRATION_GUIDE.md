# AWS + Vercel v0 통합 가이드 (최소 구성)

**목표**: AWS에서 1분마다 NOTAM 크롤링 → v0 대시보드에서 실시간 표시

**소요 시간**: 약 40분 (AWS 30분 + v0 연동 10분)

---

## 📋 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS 백엔드                          │
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │ EventBridge  │ 1분  │ Lambda       │                   │
│  │ (스케줄러)   │─────→│ 크롤러       │                   │
│  └──────────────┘      └──────┬───────┘                   │
│                               │                            │
│                               ↓ 저장                       │
│                        ┌─────────────┐                     │
│                        │ DynamoDB    │                     │
│                        │ NOTAM 테이블 │                     │
│                        └──────┬──────┘                     │
│                               │                            │
│                        ┌──────┴──────┐                     │
│                        │ Lambda API  │                     │
│                        │ (데이터 조회) │                     │
│                        └──────┬──────┘                     │
│                               │                            │
│                        ┌──────┴──────┐                     │
│                        │ API Gateway │ ← CORS 활성화       │
│                        │ REST API    │                     │
│                        └──────┬──────┘                     │
└───────────────────────────────┼────────────────────────────┘
                                │ HTTPS
                                ↓
┌───────────────────────────────┼────────────────────────────┐
│                    Vercel 프론트엔드                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ v0 NOTAM 대시보드                                    │ │
│  │ https://v0-notam-dashboard-rosy.vercel.app/          │ │
│  │                                                      │ │
│  │  - API 호출 (1분마다 자동 새로고침)                  │ │
│  │  - 통계 표시 (전체/유효/만료/신규)                   │ │
│  │  - NOTAM 목록 테이블                                 │ │
│  │  - 필터 및 검색                                      │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 STEP 1: AWS 백엔드 구축 (30분)

### 1-1. DynamoDB 테이블 생성 (5분)

1. **AWS 콘솔** → **DynamoDB** → **테이블 생성**

2. **설정**:
   ```
   테이블 이름: NOTAM_Records
   파티션 키: notam_id (문자열)
   정렬 키: (없음)

   테이블 설정: 기본 설정
   ```

3. **[테이블 생성]** 클릭

---

### 1-2. Lambda 레이어 생성 (10분)

**로컬 PowerShell**에서:

```powershell
cd C:\Users\allof\Desktop\code

# 배포 패키지 생성
.\deploy_to_aws.ps1
```

실행 결과:
```
✅ deployment/layer/lambda_layer.zip
✅ deployment/crawler/lambda_crawler.zip
✅ deployment/api/lambda_api.zip
```

**AWS 콘솔**:

1. **Lambda** → **레이어** → **레이어 생성**
2. 설정:
   ```
   이름: notam-dependencies
   .zip 파일 업로드: deployment/layer/lambda_layer.zip
   호환 런타임: Python 3.11
   ```
3. **[생성]** 클릭
4. **레이어 ARN 복사** (예: `arn:aws:lambda:ap-northeast-2:123456789012:layer:notam-dependencies:1`)

---

### 1-3. Lambda 크롤러 함수 생성 (10분)

1. **Lambda** → **함수 생성**

2. **설정**:
   ```
   함수 이름: notam-crawler
   런타임: Python 3.11
   아키텍처: x86_64
   ```

3. **[함수 생성]** 클릭

4. **코드 업로드**:
   - **업로드** → **.zip 파일** → `deployment/crawler/lambda_crawler.zip`
   - **[저장]** 클릭

5. **레이어 추가**:
   - **코드** 탭 → **레이어** → **레이어 추가**
   - **사용자 지정 레이어** → `notam-dependencies` 선택
   - **[추가]** 클릭

6. **환경 변수 설정**:
   - **구성** → **환경 변수** → **편집**
   - 추가:
     ```
     DYNAMODB_TABLE_NOTAMS = NOTAM_Records
     AWS_REGION = ap-northeast-2
     ```

7. **제한 시간 설정**:
   - **구성** → **일반 구성** → **편집**
   - **제한 시간**: 3분 0초
   - **[저장]** 클릭

8. **IAM 권한 추가**:
   - **구성** → **권한** → 역할 이름 클릭
   - **권한 추가** → **정책 연결**
   - 검색: `AmazonDynamoDBFullAccess`
   - ☑ 체크 → **[권한 추가]** 클릭

9. **테스트 실행**:
   - **테스트** 탭 → **테스트** 클릭
   - 결과 확인: `"statusCode": 200`

---

### 1-4. EventBridge 스케줄 설정 (5분)

1. **EventBridge** → **규칙** → **규칙 생성**

2. **설정**:
   ```
   이름: notam-crawler-schedule
   규칙 유형: 일정

   일정 패턴:
   - cron 표현식
   - cron(* * * * ? *)  ← 1분마다

   대상:
   - AWS 서비스
   - Lambda 함수
   - notam-crawler
   ```

3. **[규칙 생성]** 클릭

4. **확인**: 1분 후 DynamoDB 테이블에 데이터 확인
   - DynamoDB → `NOTAM_Records` → **항목 탐색**

---

### 1-5. Lambda API 함수 생성 (10분)

1. **Lambda** → **함수 생성**

2. **설정**:
   ```
   함수 이름: notam-api
   런타임: Python 3.11
   ```

3. **코드 업로드**:
   - `.zip 파일` → `deployment/api/lambda_api.zip`

4. **레이어 추가**: `notam-dependencies`

5. **환경 변수**:
   ```
   DYNAMODB_TABLE_NOTAMS = NOTAM_Records
   AWS_REGION = ap-northeast-2
   ```

6. **IAM 권한**: `AmazonDynamoDBReadOnlyAccess`

---

### 1-6. API Gateway 생성 (10분)

1. **API Gateway** → **API 생성** → **REST API** (Public) → **구축**

2. **설정**:
   ```
   프로토콜: REST
   새 API 생성
   이름: notam-api
   엔드포인트 유형: 지역
   ```

3. **리소스 생성**:

   **경로 1**: `/notams` (NOTAM 목록)
   - **작업** → **리소스 생성**
   - 리소스 이름: `notams`
   - **CORS 활성화** ☑
   - **[리소스 생성]** 클릭

   **메서드 생성**: `GET`
   - `/notams` 선택 → **작업** → **메서드 생성** → `GET`
   - 통합 유형: **Lambda 함수**
   - Lambda 함수: `notam-api`
   - **[저장]** 클릭

   **경로 2**: `/stats` (통계)
   - 리소스 이름: `stats`
   - CORS 활성화 ☑
   - 메서드: `GET` → Lambda `notam-api`

4. **CORS 설정**:
   - 각 리소스(`/notams`, `/stats`) 선택
   - **작업** → **CORS 활성화**
   - 설정:
     ```
     Access-Control-Allow-Origin: *
     Access-Control-Allow-Headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token
     ```
   - **[CORS를 활성화하고 기존의 CORS 헤더를 대체]** 클릭

5. **API 배포**:
   - **작업** → **API 배포**
   - 배포 스테이지: **[새 스테이지]**
   - 스테이지 이름: `prod`
   - **[배포]** 클릭

6. **API URL 복사**:
   ```
   https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod
   ```

---

## 🔗 STEP 2: v0 프론트엔드 연동 (10분)

### 2-1. v0 프로젝트 다운로드

1. **v0 대시보드** → **Export** → **Download code**
2. 압축 해제 → 폴더 열기

---

### 2-2. API 엔드포인트 설정

**`.env.local` 파일 생성**:

```bash
# AWS API Gateway URL
NEXT_PUBLIC_API_BASE_URL=https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod
```

**`xxxxxxxxxx`** 부분을 **1-6에서 복사한 API URL**로 변경

---

### 2-3. API 호출 코드 수정

v0가 생성한 코드에서 API 호출 부분을 찾아 수정:

**예시** (`app/page.tsx` 또는 `components/dashboard.tsx`):

```typescript
// 기존 (mock 데이터)
const fetchNOTAMs = async () => {
  // mock data...
}

// 수정 (AWS API 호출)
const fetchNOTAMs = async () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  try {
    const response = await fetch(`${baseUrl}/notams?limit=100`);
    const data = await response.json();

    // API 응답 파싱
    const body = JSON.parse(data.body);
    return body.notams || [];
  } catch (error) {
    console.error('Failed to fetch NOTAMs:', error);
    return [];
  }
}

const fetchStats = async () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  try {
    const response = await fetch(`${baseUrl}/stats`);
    const data = await response.json();

    const body = JSON.parse(data.body);
    return body.stats;
  } catch (error) {
    console.error('Failed to fetch stats:', error);
    return {
      total_notams: 0,
      active_notams: 0,
      expired_notams: 0,
      new_today: 0,
      last_crawl_time: '',
      last_crawl_status: 'unknown'
    };
  }
}
```

---

### 2-4. Vercel 재배포

**로컬에서** (v0 프로젝트 폴더):

```bash
# 패키지 설치
npm install

# 로컬 테스트
npm run dev
# 브라우저: http://localhost:3000 접속 → 데이터 확인

# Vercel 배포
npx vercel --prod
```

또는 **GitHub 연동**:
1. GitHub에 푸시
2. Vercel → **Import Project** → GitHub 저장소 선택
3. **환경 변수 추가**: `NEXT_PUBLIC_API_BASE_URL`
4. **Deploy** 클릭

---

## ✅ 완료 확인

### 1. AWS 크롤링 확인
- **DynamoDB** → `NOTAM_Records` → **항목 탐색**
- NOTAM 데이터 확인 (1분마다 추가)

### 2. API 테스트
브라우저에서:
```
https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod/notams
https://xxxxxxxxxx.execute-api.ap-northeast-2.amazonaws.com/prod/stats
```

응답 확인:
```json
{
  "statusCode": 200,
  "body": "{\"notams\": [...], \"count\": 42}"
}
```

### 3. v0 대시보드 확인
```
https://v0-notam-dashboard-rosy.vercel.app/
```

**확인 항목**:
- ✅ 통계 카드에 실제 숫자 표시
- ✅ NOTAM 목록 테이블에 데이터 표시
- ✅ 1분마다 자동 새로고침
- ✅ 필터 및 검색 작동

---

## 🎯 전체 흐름 요약

```
1분마다:
  EventBridge → Lambda 크롤러 실행
              → AIM 포털에서 NOTAM 가져오기
              → DynamoDB에 저장

사용자가 대시보드 접속:
  v0 대시보드 → API Gateway 호출
              → Lambda API가 DynamoDB 조회
              → 데이터 반환
              → 화면에 표시
```

---

## 📊 예상 비용

- **DynamoDB**: 무료 (25GB, 읽기 25만/쓰기 25만 무료)
- **Lambda**: 무료 (100만 요청/월 무료)
- **API Gateway**: 무료 (100만 요청/월 무료)
- **Vercel**: 무료 (Hobby 플랜)

**총 비용**: 무료 (프리 티어 범위 내)

---

## 🔧 트러블슈팅

### 문제 1: v0 대시보드에 데이터 안 보임
**원인**: CORS 오류
**해결**:
1. API Gateway → 리소스 선택 → **작업** → **CORS 활성화**
2. `Access-Control-Allow-Origin: *` 확인
3. **API 재배포** (작업 → API 배포)

### 문제 2: API 호출 실패 (401, 403)
**원인**: Lambda 권한 부족
**해결**:
1. Lambda → **구성** → **권한**
2. IAM 역할에 `AmazonDynamoDBFullAccess` 확인

### 문제 3: DynamoDB에 데이터 없음
**원인**: Lambda 크롤러 실패
**해결**:
1. Lambda → **모니터** → **CloudWatch의 로그 보기**
2. 오류 메시지 확인 (네트워크 오류, 파싱 오류 등)

---

## 📞 다음 단계

제가 도와드릴 것:

1. ✅ **AWS 백엔드 구축** (위 STEP 1 따라하기)
2. ✅ **v0 코드 수정** (API 연동)
3. ✅ **Vercel 재배포**
4. ✅ **통합 테스트**

**지금 바로**: AWS STEP 1-1 (DynamoDB 테이블 생성)부터 시작하세요!
막히는 부분이 있으면 언제든 물어보세요.
