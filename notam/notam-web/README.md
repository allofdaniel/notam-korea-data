# NOTAM 모니터링 대시보드

대한민국 항공 공지(NOTAM) 실시간 모니터링 웹 애플리케이션

## 라이브 데모

**Production URL:** https://notam-web.vercel.app

## 주요 기능

### 대시보드
- 전체/활성/만료/예정 NOTAM 통계
- 최근 7일 활성 NOTAM 추세 차트
- NOTAM 상태 분포 파이 차트
- 일일 신규/만료 NOTAM 변화 차트

### 지도 뷰
- Mapbox 기반 인터랙티브 지도
- 원형 및 다각형 NOTAM 영역 시각화
- 호버 시 NOTAM 정보 툴팁
- 클릭 시 상세 정보 패널 표시
- **반경별 필터링** (10km ~ 1000km)
- 필터 프리셋 버튼 (50km, 100km, 200km, 500km, 전체)

### NOTAM 리스트
- 검색 기능 (ID, 공항, 내용)
- 상태별 필터 (활성/만료/예정/트리거)
- 공항별 필터 (515개 공항)
- 페이지네이션 (20개씩)
- **"지도에서 보기"** 버튼으로 지도 연동

### 상세 정보 패널
- Q-Code 의미 해석 (한국어)
- 시작/종료 시간 표시
- 영향 반경 및 중심 좌표
- 원본 NOTAM 텍스트 및 Q-Line

## 기술 스택

- **Frontend:** React 18 + Vite
- **지도:** Mapbox GL JS + react-map-gl
- **차트:** Recharts
- **HTTP Client:** Axios
- **배포:** Vercel
- **백엔드 API:** AWS EC2 (Python FastAPI)
- **데이터 저장:** AWS S3 (SQLite DB)

## 최근 업데이트 (2024-12)

### v2.0 개선사항

1. **Q-Code 해석 기능 개선**
   - QCODE_SUBJECT/CONDITION 사전 추가
   - 5자 Q-Code 파싱 (예: QRPCN → "금지 구역 폐쇄")
   - 한국어 의미 표시

2. **대형 NOTAM 필터 기능**
   - 반경 기반 필터링 (기본 500km)
   - 슬라이더 및 프리셋 버튼 UI
   - 필터된 NOTAM 개수 표시

3. **리스트-지도 연동**
   - "지도에서 보기" 버튼 추가
   - 클릭 시 지도 탭으로 전환 및 해당 위치로 이동
   - NOTAM 자동 선택 및 상세 패널 표시

4. **NOTAM 파서 개선** (+11% 커버리지)
   - FIR 중심 좌표 폴백 (좌표 없는 NOTAM 지원)
   - 주요 공항 좌표 데이터베이스 추가
   - 초 단위 포함 좌표 형식 지원 (DDMMSS)
   - Q-Line 메타데이터 추출 (FIR, 고도)

5. **UI/UX 개선**
   - Aviation Control Tower 다크 테마
   - 반응형 모바일 레이아웃
   - 호버/클릭 인터랙션 개선

## 프로젝트 구조

```
notam-web/
├── src/
│   ├── components/
│   │   ├── NotamMap.jsx       # 지도 컴포넌트
│   │   ├── NotamMap.css
│   │   ├── NotamList.jsx      # 리스트 컴포넌트
│   │   ├── NotamList.css
│   │   ├── NotamDetailModal.jsx
│   │   └── NotamDetailModal.css
│   ├── utils/
│   │   ├── notamParser.js     # 좌표/Q-code 파싱
│   │   ├── notamUtils.js      # 유틸리티 함수
│   │   └── airportNames.js    # 공항명 데이터
│   ├── App.jsx                # 메인 앱
│   ├── App.css
│   └── main.jsx
├── api/
│   └── proxy.js               # Vercel API 프록시
├── public/
├── package.json
└── vite.config.js
```

## 로컬 개발

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build

# 프리뷰
npm run preview
```

## 배포

```bash
# Vercel CLI로 배포
npx vercel --prod
```

## API 엔드포인트

프록시를 통해 EC2 백엔드 API에 접근:

- `GET /api/proxy?path=/notams/stats` - 통계
- `GET /api/proxy?path=/notams/active` - 활성 NOTAM
- `GET /api/proxy?path=/notams/expired` - 만료 NOTAM
- `GET /api/proxy?path=/notams/realtime?limit=5000` - 실시간 데이터

## CI/CD (GitHub Actions)

### 자동 배포 설정

이 프로젝트는 GitHub Actions를 통해 자동 배포됩니다:

- **CI** (`ci.yml`): 모든 push/PR에서 린트 및 빌드 테스트
- **Deploy** (`deploy.yml`): main 브랜치 push 시 Vercel 자동 배포

### GitHub Secrets 설정

Repository → Settings → Secrets and variables → Actions에서 추가:

| Secret Name | 설명 | 값 확인 방법 |
|-------------|------|--------------|
| `VERCEL_TOKEN` | Vercel Access Token | [Vercel Tokens](https://vercel.com/account/tokens) |
| `VERCEL_ORG_ID` | Vercel 조직 ID | `.vercel/project.json` 참조 |
| `VERCEL_PROJECT_ID` | Vercel 프로젝트 ID | `.vercel/project.json` 참조 |
| `VITE_API_BASE_URL` | API 서버 URL | `http://3.27.240.67:8000` |
| `VITE_MAPBOX_TOKEN` | Mapbox Public Token | Mapbox 계정 확인 |

### 워크플로우

```bash
# 1. 코드 수정 후 커밋
git add .
git commit -m "feat: 새 기능 추가"

# 2. Push → 자동 CI/CD 실행
git push origin main

# 3. GitHub Actions에서 자동으로:
#    - 빌드 테스트
#    - Vercel 프로덕션 배포
```

## 라이선스

MIT License
