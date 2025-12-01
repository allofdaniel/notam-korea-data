# v0 대시보드 AWS API 연동 가이드

## 🎯 목표

v0 대시보드가 AWS API에서 실시간 NOTAM 데이터를 가져오도록 설정

---

## 📋 준비물

- ✅ v0 프로젝트: https://v0-notam-dashboard-rosy.vercel.app/
- ✅ AWS API URL: `https://402p7v6m12.execute-api.ap-southeast-2.amazonaws.com/prod`

---

## 🔧 방법 1: v0에서 직접 수정 (간단)

### 1️⃣ v0 대시보드 접속

https://v0.dev → 프로젝트 열기

### 2️⃣ API 엔드포인트 설정

코드에서 API URL을 찾아서 변경:

**변경 전**:
```typescript
const API_URL = "http://localhost:3000/api";
```

**변경 후**:
```typescript
const API_URL = "https://402p7v6m12.execute-api.ap-southeast-2.amazonaws.com/prod";
```

### 3️⃣ 데이터 fetch 함수 수정

```typescript
async function fetchNOTAMs() {
  try {
    const response = await fetch(`${API_URL}/notams?data_source=international&limit=100`);
    const data = await response.json();

    return data.data || []; // API 응답에서 data 배열 추출
  } catch (error) {
    console.error('Failed to fetch NOTAMs:', error);
    return [];
  }
}

async function fetchStats() {
  try {
    const response = await fetch(`${API_URL}/stats`);
    const data = await response.json();

    return {
      total: data.total || 0,
      active: data.data?.filter(n => n.status === 'ACTIVE').length || 0,
      expired: data.data?.filter(n => n.status === 'EXPIRED').length || 0,
      newToday: data.data?.filter(n => {
        const today = new Date().toISOString().split('T')[0];
        return n.crawl_timestamp?.startsWith(today);
      }).length || 0
    };
  } catch (error) {
    console.error('Failed to fetch stats:', error);
    return { total: 0, active: 0, expired: 0, newToday: 0 };
  }
}
```

### 4️⃣ 재배포

v0에서 **"Deploy"** 클릭

---

## 🔧 방법 2: 로컬에서 수정 (고급)

### 1️⃣ v0 프로젝트 다운로드

v0 대시보드 → **Export** → **Download code**

### 2️⃣ 환경 변수 설정

프로젝트 루트에 `.env.local` 파일 생성:

```bash
NEXT_PUBLIC_API_BASE_URL=https://402p7v6m12.execute-api.ap-southeast-2.amazonaws.com/prod
```

### 3️⃣ API 호출 코드 수정

예시 (`app/page.tsx` 또는 해당 파일):

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

// NOTAM 목록 가져오기
async function fetchNOTAMs(dataSource = 'international', limit = 100) {
  const response = await fetch(
    `${API_URL}/notams?data_source=${dataSource}&limit=${limit}`
  );
  const data = await response.json();
  return data.data || [];
}

// 통계 가져오기 (선택사항)
async function fetchStats() {
  const response = await fetch(`${API_URL}/stats`);
  const data = await response.json();
  return data;
}
```

### 4️⃣ 로컬 테스트

```bash
npm install
npm run dev
```

브라우저: http://localhost:3000

### 5️⃣ Vercel 배포

```bash
npx vercel --prod
```

또는 GitHub에 푸시 → Vercel 자동 배포

**환경 변수 설정 필수**:
- Vercel 프로젝트 → **Settings** → **Environment Variables**
- `NEXT_PUBLIC_API_BASE_URL` 추가

---

## 📊 API 엔드포인트

### 1. NOTAM 목록 조회

```
GET /notams?data_source=international&limit=100
```

**응답**:
```json
{
  "status": "success",
  "total": 28,
  "data_source": "international",
  "data": [
    {
      "notam_id": "A1486/25",
      "location": "RKSS",
      "notam_type": "A",
      "status": "ACTIVE",
      "issue_time": "2511130314",
      "start_time": "2511131400",
      "end_time": "2511132000",
      "qcode": "QWULW",
      "full_text": "...",
      "data_source": "international",
      "crawl_timestamp": "2025-11-13 05:06:23"
    },
    ...
  ]
}
```

### 2. 통계 조회 (선택사항)

```
GET /stats
```

### 3. 필터링

```
GET /notams?data_source=international&location=RKSS&limit=50
```

---

## ✅ 확인 사항

배포 후 대시보드에서:

- ✅ NOTAM 데이터가 표시되는가?
- ✅ 통계가 정확한가?
- ✅ 자동 새로고침이 작동하는가?

---

## 🚨 트러블슈팅

### CORS 오류가 나는 경우

API Gateway에서 CORS 설정 확인:
1. API Gateway → 리소스 선택
2. **작업** → **CORS 활성화**
3. `Access-Control-Allow-Origin: *` 확인
4. **API 재배포**

### 데이터가 안 나오는 경우

1. 브라우저 개발자 도구 (F12) → **Network** 탭 확인
2. API 호출이 성공하는지 확인 (200 OK)
3. 응답 데이터 구조 확인

### 환경 변수가 적용 안 되는 경우

- `.env.local` 파일이 `.gitignore`에 있는지 확인
- Vercel 환경 변수가 설정되어 있는지 확인
- 재배포 필요

---

## 🎉 완료!

v0 대시보드가 AWS API와 연동되어 **실시간 NOTAM 모니터링 시스템** 완성!

**최종 구조**:

```
사용자
  ↓
v0 대시보드 (Vercel)
  ↓ API 호출
AWS API Gateway
  ↓
Lambda API 함수
  ↓
DynamoDB (NOTAM 데이터)
  ↑
Lambda 크롤러 (1분마다)
  ↑
로컬 크롤러 (필요시 수동)
```
