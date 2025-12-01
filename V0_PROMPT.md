# Vercel v0 프롬프트: NOTAM 모니터링 대시보드

## 프롬프트 (v0에 복사해서 붙여넣기)

```
Create a modern NOTAM (Notice to Airmen) monitoring dashboard with the following features:

### Main Dashboard Page
1. **Real-time NOTAM List**
   - Table showing NOTAM records with columns: ID, Location (airport code), Type, Issue Time, Valid Period (Start-End), Status
   - Filter options: Data Source (Domestic/International), Location (airport dropdown), Date Range
   - Search bar for NOTAM ID or content
   - Pagination (20 items per page)
   - Auto-refresh every 60 seconds with loading indicator

2. **Statistics Cards** (Top of page)
   - Total NOTAMs (current count)
   - Active NOTAMs (currently valid)
   - Expired NOTAMs (past end time)
   - New Today (issued in last 24h)
   - Last Crawl Time with success/fail status badge

3. **NOTAM Detail Modal**
   - Click on any row to open modal
   - Show full NOTAM text (Korean)
   - Q-Code interpretation
   - Validity period with countdown timer
   - Location map (if possible)
   - Raw JSON data (collapsible section)

### Color Scheme
- Use aviation-themed colors: dark blue (#1e3a8a), sky blue (#3b82f6), white, gray
- Status badges: green (active), red (expired), yellow (expiring soon <2h)
- Modern, clean design with card-based layout

### Technical Requirements
- Use Next.js 14 with App Router
- TypeScript
- Tailwind CSS for styling
- shadcn/ui components (Table, Card, Badge, Button, Dialog, Select, Input)
- Use Lucide icons (Plane, Search, Filter, RefreshCw, Calendar, MapPin)
- Responsive design (mobile-friendly)

### API Integration Placeholder
- Create mock API calls with TypeScript interfaces:
  ```typescript
  interface NOTAM {
    notam_id: string;
    location: string;
    notam_type: string;
    issue_time: string;
    start_time: string;
    end_time: string;
    qcode: string;
    full_text: string;
    data_source: 'domestic' | 'international';
    crawl_timestamp: string;
  }

  interface Stats {
    total_notams: number;
    active_notams: number;
    expired_notams: number;
    new_today: number;
    last_crawl_time: string;
    last_crawl_status: 'success' | 'failed';
  }
  ```

- API endpoints to implement later:
  - GET /api/notams?data_source=&location=&limit=20&offset=0
  - GET /api/notams/{id}
  - GET /api/stats

### Additional Features
- Loading skeletons while fetching data
- Error handling with retry button
- Export to CSV button
- Dark mode toggle
- Korean language labels (UI labels in Korean)
```

---

## 한글 버전 (선택사항)

```
현대적인 NOTAM(항공고시보) 모니터링 대시보드를 만들어주세요:

### 메인 대시보드
1. **실시간 NOTAM 목록**
   - 테이블: ID, 공항코드, 유형, 발행시간, 유효기간, 상태
   - 필터: 국내/국제, 공항, 날짜 범위
   - 검색창 (ID/내용)
   - 페이지네이션 (20개/페이지)
   - 1분마다 자동 새로고침

2. **통계 카드**
   - 전체 NOTAM 수
   - 현재 유효한 NOTAM
   - 만료된 NOTAM
   - 오늘 신규 발행
   - 마지막 크롤링 시간 (성공/실패 뱃지)

3. **상세 정보 모달**
   - 행 클릭 시 팝업
   - 전체 텍스트 표시
   - Q-Code 해석
   - 유효기간 카운트다운
   - 원본 JSON (접기 가능)

### 디자인
- 항공 테마: 진한 파란색, 하늘색, 흰색
- 상태 뱃지: 녹색(유효), 빨간색(만료), 노란색(곧 만료)
- 카드 기반 레이아웃

### 기술 스택
- Next.js 14, TypeScript, Tailwind, shadcn/ui
- 반응형 디자인
- 한글 UI

API는 나중에 연결할 것이므로, 타입 인터페이스와 mock 데이터만 생성
```

---

## 사용 방법

### 1단계: v0에서 생성
1. https://v0.dev 접속
2. 위 프롬프트 복사 → 붙여넣기
3. "Generate" 클릭
4. 생성된 코드 다운로드

### 2단계: AWS API 연동 (제가 도와드림)
v0가 생성한 코드를 받으면:
1. API 엔드포인트를 AWS API Gateway URL로 변경
2. 환경변수 설정 (.env.local)
3. Vercel에 배포

---

## 예상 결과

v0가 생성할 대시보드:
```
┌─────────────────────────────────────────────────┐
│  📊 NOTAM 모니터링 대시보드          🔄 새로고침 │
├─────────────────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │
│  │ 전체 │ │ 유효 │ │ 만료 │ │ 신규 │           │
│  │  42  │ │  28  │ │  14  │ │   5  │           │
│  └──────┘ └──────┘ └──────┘ └──────┘           │
├─────────────────────────────────────────────────┤
│  🔍 [검색]  📍[국내▼] 📅[날짜▼]                 │
├─────────────────────────────────────────────────┤
│  ID       공항   유형   발행시간    상태        │
│  ─────────────────────────────────────────      │
│  A0123  RKSI   RWY   11-10 14:30  🟢 유효      │
│  A0124  RKSS   TWY   11-10 15:00  🟡 곧 만료   │
│  A0125  RKPC   APR   11-09 08:00  🔴 만료      │
│  ...                                            │
└─────────────────────────────────────────────────┘
```

---

## 다음 단계

1. **지금 바로**: 위 프롬프트를 v0에 입력
2. **생성 완료 후**: 저에게 알려주세요 → API 연동 코드 작성
3. **배포**: Vercel에 배포 (무료)

v0가 생성한 코드를 보여주시면, AWS API Gateway와 연동하는 코드를 추가해드릴게요!
