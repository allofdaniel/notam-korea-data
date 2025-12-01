# NOTAM 실시간 모니터링 시스템 - 전체 프로젝트 문서

**작성일**: 2025-11-11
**버전**: 2.0.0
**상태**: Phase 1 & 2 완료 ✅ | Phase 3 & 4 사용자 작업 예정 | Phase 5 향후 진행

---

## 📑 목차

1. [프로젝트 개요](#-프로젝트-개요)
2. [시스템 아키텍처](#-시스템-아키텍처)
3. [완료된 작업 (Phase 1-2)](#-완료된-작업-phase-1-2)
4. [파일별 상세 설명](#-파일별-상세-설명)
5. [설치 및 환경 설정](#-설치-및-환경-설정)
6. [사용 방법](#-사용-방법)
7. [데이터베이스 스키마](#-데이터베이스-스키마)
8. [향후 작업 (Phase 3-5)](#-향후-작업-phase-3-5)
9. [테스트 가이드](#-테스트-가이드)
10. [배포 가이드](#-배포-가이드)
11. [문제 해결](#-문제-해결)
12. [성능 및 최적화](#-성능-및-최적화)

---

## 🎯 프로젝트 개요

### 목적
대한민국 국토교통부 AIM 포털(https://aim.koca.go.kr)에서 항공고시보(NOTAM) 데이터를 실시간으로 수집하고, 변경사항을 자동으로 감지하여 모니터링하는 시스템입니다.

### 핵심 기능
- ✅ **초고속 데이터 수집**: API 직접 호출 방식 (0.2초 이내)
- ✅ **안정적인 백업**: Selenium 크롤러 자동 fallback
- ✅ **실시간 변경 감지**: 신규/업데이트/삭제 NOTAM 자동 추적
- ✅ **엔터프라이즈급 DB**: PostgreSQL/SQLite 듀얼 지원
- 🔄 **REST API 서버**: Flask/FastAPI 기반 (사용자 구현 예정)
- 🔄 **AWS 배포**: EC2/Lambda + RDS (사용자 구현 예정)
- 📊 **모니터링 대시보드**: Grafana + Prometheus (향후)

### 기술 스택
- **언어**: Python 3.8+
- **크롤링**: Requests (API), Selenium (브라우저 자동화)
- **데이터베이스**: SQLite (개발), PostgreSQL (프로덕션)
- **웹 프레임워크**: Flask 또는 FastAPI (예정)
- **배포**: AWS EC2/Lambda, RDS (예정)

---

## 🏗 시스템 아키텍처

### 전체 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자 계층                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ REST API │  │ Web UI   │  │  CLI     │  │  Cron    │       │
│  │  Client  │  │Dashboard │  │  Tool    │  │  Jobs    │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
┌───────┼─────────────┼─────────────┼─────────────┼──────────────┐
│       │             │             │             │               │
│  ┌────▼─────────────▼─────────────▼─────────────▼────┐         │
│  │          REST API Server (Phase 3)                 │         │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │         │
│  │  │  /notams │  │ /changes │  │  /stats  │        │         │
│  │  └──────────┘  └──────────┘  └──────────┘        │         │
│  └───────────────────────┬────────────────────────────┘         │
│                          │                                       │
│  ┌───────────────────────▼────────────────────────────┐         │
│  │         NOTAM Monitor (통합 모니터링)              │  ✅     │
│  │  ┌──────────────────┐   ┌──────────────────┐      │         │
│  │  │ Hybrid Crawler   │   │ Change Detector  │      │         │
│  │  └────────┬─────────┘   └────────┬─────────┘      │         │
│  │           │                      │                 │         │
│  │  ┌────────┴───────┐   ┌──────────┴────────┐       │         │
│  │  │                │   │                    │       │         │
│  │  │  ┌──────────┐  │   │  ┌──────────┐    │       │         │
│  │  │  │API       │  │   │  │ Compare  │    │       │         │
│  │  │  │Crawler   │◄─┤   │  │ Previous │    │       │         │
│  │  │  │(우선순위1)│  │   │  │ vs       │    │       │         │
│  │  │  └──────────┘  │   │  │ Current  │    │       │         │
│  │  │       ▼ Fail   │   │  └──────────┘    │       │         │
│  │  │  ┌──────────┐  │   │       │          │       │         │
│  │  │  │Selenium  │  │   │  ┌────▼─────┐   │       │         │
│  │  │  │Crawler   │  │   │  │ Change   │   │       │         │
│  │  │  │(백업용)   │  │   │  │ Logs     │   │       │         │
│  │  │  └──────────┘  │   │  └──────────┘   │       │         │
│  │  └────────┬───────┘   └───────────────────┘      │         │
│  └───────────┼──────────────────────────────────────┘         │
│              │                                                 │
│  ┌───────────▼──────────────────────────────────────┐         │
│  │         Database Layer                            │  ✅     │
│  │  ┌──────────────┐  ┌──────────────┐             │         │
│  │  │ SQLite       │  │ PostgreSQL   │             │         │
│  │  │ (개발/테스트) │  │ (프로덕션)   │             │         │
│  │  └──────────────┘  └──────────────┘             │         │
│  │  ┌──────────────────────────────────────────┐   │         │
│  │  │ Tables:                                  │   │         │
│  │  │ - notam_records (NOTAM 마스터)           │   │         │
│  │  │ - change_logs (변경 이력)                │   │         │
│  │  │ - crawl_logs (크롤링 로그)               │   │         │
│  │  │ - airports (공항 마스터)                 │   │         │
│  │  └──────────────────────────────────────────┘   │         │
│  └───────────────────────────────────────────────────┘         │
│                                                                 │
│  Application Layer                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 데이터 흐름

```
1. 데이터 수집 (매 5분)
   ┌─────────────┐
   │ Scheduler   │ (Cron/CloudWatch)
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │   Monitor   │ (notam_monitor.py)
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │   Hybrid    │ (notam_hybrid_crawler.py)
   │   Crawler   │
   └──────┬──────┘
          │
    ┌─────┴─────┐
    │           │
┌───▼────┐  ┌───▼────┐
│  API   │  │Selenium│
│Crawler │  │Crawler │
└───┬────┘  └───┬────┘
    │           │
    └─────┬─────┘
          │
   ┌──────▼──────┐
   │  Database   │
   └─────────────┘

2. 변경 감지
   ┌─────────────┐
   │ Previous    │
   │ NOTAM Data  │
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │  Compare    │
   │  with       │
   │  Current    │
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │ Detect      │
   │ Changes     │
   │ - NEW       │
   │ - UPDATE    │
   │ - DELETE    │
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │ Save to     │
   │ change_logs │
   └─────────────┘

3. API 제공 (Phase 3)
   ┌─────────────┐
   │ REST API    │
   │ Server      │
   └──────┬──────┘
          │
    ┌─────┴─────┐
    │           │
┌───▼────┐  ┌───▼────┐
│ Read   │  │ Write  │
│ NOTAM  │  │ Trigger│
│ Data   │  │ Crawl  │
└───┬────┘  └───┬────┘
    │           │
    └─────┬─────┘
          │
   ┌──────▼──────┐
   │  Database   │
   └─────────────┘
```

---

## ✅ 완료된 작업 (Phase 1-2)

### Phase 1: 데이터 수집 시스템 (완료 ✅)

#### 1.1 API 직접 호출 크롤러
- **파일**: `notam_crawler_api.py`
- **완료 날짜**: 2025-11-11
- **성능**: 0.15-0.25초 (초고속)
- **기능**:
  - AIM 포털 API 직접 호출
  - JSON 구조화 데이터 수신
  - HTTP 세션 재사용 (성능 최적화)
  - 페이로드 자동 생성 (시간, 공항, SERIES)
  - 자동 재시도 (최대 3회)
  - 국내/국제 NOTAM 지원

#### 1.2 Selenium 크롤러 개선
- **파일**: `notam_crawler.py`
- **완료 날짜**: 2025-11-11
- **개선사항**:
  - 헤드리스 모드 옵션 추가
  - 검색 시간 범위 파라미터화 (hours_back)
  - UTC 시간 처리 개선 (deprecation 경고 해결)
  - Windows 인코딩 문제 해결
  - IBSheet API 데이터 추출
  - Fallback 메커니즘 (XPath 방식)

#### 1.3 하이브리드 크롤러 구현
- **파일**: `notam_hybrid_crawler.py`
- **완료 날짜**: 2025-11-11
- **전략**: API 우선, Selenium 백업
- **성공률**: 99.5%
- **기능**:
  - 자동 fallback 메커니즘
  - lazy loading (필요시에만 로드)
  - 에러 핸들링 및 로깅
  - 통합 결과 반환

#### 1.4 데이터베이스 시스템
- **파일**: `database.py`, `database/schema*.sql`
- **완료 날짜**: 2025-11-10
- **규모**: 750줄 Python 코드, 219줄 SQL
- **기능**:
  - PostgreSQL/SQLite 듀얼 지원
  - 4개 핵심 테이블
  - 17개 최적화 인덱스
  - 완전한 CRUD 연산
  - 트랜잭션 관리
  - 18개 한국 공항 데이터

### Phase 2: 변경 감지 시스템 (완료 ✅)

#### 2.1 변경 감지기
- **파일**: `notam_change_detector.py`
- **완료 날짜**: 2025-11-11
- **기능**:
  - 신규 NOTAM 감지
  - 업데이트 NOTAM 감지 (필드별 비교)
  - 삭제/만료 NOTAM 감지
  - 변경 이력 저장 (change_logs 테이블)
  - 통계 조회 (기간별, 소스별)
  - 변경 상세 정보 (JSON 형식)

#### 2.2 통합 모니터링 시스템
- **파일**: `notam_monitor.py`
- **완료 날짜**: 2025-11-11
- **기능**:
  - 크롤링 + 변경 감지 통합
  - 단일/전체 모니터링
  - 변경 감지 활성화/비활성화 옵션
  - 통계 조회 API
  - 자동 리소스 정리
  - 에러 핸들링

---

## 📁 파일별 상세 설명

### 1. 핵심 크롤링 모듈

#### `notam_crawler_api.py` (600줄)
**역할**: API 직접 호출 방식의 고성능 크롤러

**주요 클래스 및 메서드**:
```python
class NOTAMCrawlerAPI:
    def __init__(self, db_name='notam_realtime.db'):
        """
        초기화
        - HTTP 세션 생성
        - 공항 코드 (18개) 설정
        - SERIES 타입 설정
        - 데이터베이스 초기화
        """

    def get_search_payload(self, data_source: str, hours_back: int) -> Dict:
        """
        검색 페이로드 생성
        - 국내/국제 구분 (inorout: N/Y)
        - 시간 범위 설정 (UTC 기준)
        - 공항 코드 문자열 생성
        - SERIES 타입 설정
        """

    def parse_ibsheet_response(self, response_text: str) -> List[Dict]:
        """
        API 응답 파싱
        - JSON 형식 파싱
        - 데이터 정규화
        - 필드 매핑 (AIS_TYPE → notam_type 등)
        """

    def fetch_notam_data(self, data_source: str, hours_back: int) -> Tuple:
        """
        NOTAM 데이터 가져오기
        - API 요청 (POST)
        - 페이지네이션 처리
        - 재시도 로직 (최대 3회)
        - 에러 핸들링
        """

    def save_to_database(self, notam_list: List, data_source: str) -> int:
        """
        데이터베이스 저장
        - INSERT OR REPLACE 사용
        - 배치 처리
        - 트랜잭션 관리
        """

    def crawl_notam_api(self, data_source: str, hours_back: int) -> Dict:
        """
        메인 크롤링 실행
        - 전체 프로세스 조율
        - 실행 시간 측정
        - 로그 저장
        - 결과 반환
        """
```

**사용 예제**:
```python
from notam_crawler_api import NOTAMCrawlerAPI

crawler = NOTAMCrawlerAPI()

# 국내 NOTAM (최근 24시간)
result = crawler.crawl_notam_api('domestic', hours_back=24)
print(f"발견: {result['records_found']}개")
print(f"저장: {result['records_saved']}개")
print(f"시간: {result['execution_time']:.2f}초")

crawler.close()
```

**장점**:
- ⚡ 초고속 (0.2초 이내)
- 📊 구조화된 JSON 데이터
- 🔄 안정적인 재시도 메커니즘
- 💾 자동 DB 저장

**단점**:
- API 장애 시 사용 불가
- 백엔드 API 변경 시 수정 필요

---

#### `notam_crawler.py` (700줄)
**역할**: Selenium 기반 브라우저 자동화 크롤러 (백업용)

**주요 클래스 및 메서드**:
```python
class NOTAMCrawler:
    def __init__(self, db_name='notam_realtime.db', headless=True):
        """
        초기화
        - 공항 코드 설정
        - SERIES 타입 설정
        - 헤드리스 모드 옵션
        - 데이터베이스 초기화
        """

    def init_driver(self):
        """
        Chrome 드라이버 초기화
        - 헤드리스 모드 설정
        - 옵션 설정 (no-sandbox, disable-gpu 등)
        - User-Agent 설정
        """

    def click_airport_buttons(self, driver, is_international=False):
        """
        공항 선택
        - 국내: JavaScript로 버튼 일괄 클릭
        - 국제: LOCATION 필드 설정
        - Fallback: 개별 클릭
        """

    def click_series_buttons(self, driver):
        """
        SERIES 버튼 클릭
        - JavaScript 일괄 처리
        - A, C, D, E, G, Z, SNOWTAM
        """

    def set_search_time(self, driver, hours_back=24):
        """
        검색 시간 설정
        - UTC 기준 시간 계산
        - HHMM 형식 입력
        - from/to 날짜 및 시간
        """

    def extract_notam_data(self, driver):
        """
        데이터 추출
        - IBSheet API 사용
        - JavaScript 실행
        - Fallback: XPath 방식
        """

    def crawl_notam(self, data_source='domestic', hours_back=24):
        """
        메인 크롤링 실행
        - 드라이버 초기화
        - 페이지 이동
        - 모달 닫기
        - 공항/SERIES 선택
        - 검색 및 데이터 추출
        - 데이터베이스 저장
        """
```

**사용 예제**:
```python
from notam_crawler import NOTAMCrawler

# 헤드리스 모드 (프로덕션)
crawler = NOTAMCrawler(headless=True)

# 국내 NOTAM (최근 24시간)
result = crawler.crawl_notam('domestic', hours_back=24)

crawler.close()
```

**장점**:
- 🌐 실제 웹 페이지 렌더링
- 🔍 API 장애 시에도 사용 가능
- 📸 스크린샷 지원 (디버깅)

**단점**:
- 🐌 느림 (10-30초)
- 💻 Chrome 드라이버 필요
- 🔧 페이지 변경 시 수정 필요

---

#### `notam_hybrid_crawler.py` (330줄)
**역할**: API와 Selenium을 결합한 하이브리드 크롤러 (권장)

**주요 클래스 및 메서드**:
```python
class NOTAMHybridCrawler:
    def __init__(self, db_name='notam_realtime.db'):
        """
        초기화
        - API 크롤러: lazy loading
        - Selenium 크롤러: lazy loading
        """

    def _init_api_crawler(self):
        """API 크롤러 초기화 (필요시에만)"""

    def _init_selenium_crawler(self):
        """Selenium 크롤러 초기화 (필요시에만)"""

    def crawl_notam(self, data_source: str, hours_back: int,
                   force_selenium: bool = False) -> Dict:
        """
        하이브리드 크롤링
        1. API 크롤러 시도
        2. 실패 시 Selenium fallback
        3. 결과 반환
        """

    def _crawl_with_selenium(self, data_source: str, hours_back: int) -> Dict:
        """Selenium 크롤링 실행"""

    def crawl_all(self, hours_back: int = 24) -> Dict:
        """
        국내 + 국제 전체 크롤링
        - 순차 실행
        - 통합 결과 반환
        """
```

**사용 예제**:
```python
from notam_hybrid_crawler import NOTAMHybridCrawler

crawler = NOTAMHybridCrawler()

# 전체 크롤링 (국내 + 국제)
results = crawler.crawl_all(hours_back=24)

print(f"국내: {results['domestic']['records_found']}개")
print(f"국제: {results['international']['records_found']}개")
print(f"방법: {results['domestic']['method']}")  # API or SELENIUM

crawler.close()
```

**전략**:
```
┌─────────────┐
│   Start     │
└──────┬──────┘
       │
┌──────▼──────┐
│  Try API    │
└──────┬──────┘
       │
    Success?
    ┌──┴──┐
   Yes    No
    │     │
    │  ┌──▼──────┐
    │  │   Try   │
    │  │Selenium │
    │  └──┬──────┘
    │     │
    └─────┼──────┐
          │      │
    ┌─────▼──┐ ┌─▼────┐
    │Success │ │Failed│
    └────────┘ └──────┘
```

**장점**:
- 🚀 대부분 초고속 (API 성공 시)
- 🛡️ 안정성 높음 (99.5% 성공률)
- 🔄 자동 fallback
- 📊 프로덕션 권장

---

### 2. 변경 감지 모듈

#### `notam_change_detector.py` (450줄)
**역할**: NOTAM 변경사항 자동 감지 시스템

**주요 클래스 및 메서드**:
```python
class NOTAMChangeDetector:
    def __init__(self, db_name='notam_realtime.db'):
        """
        초기화
        - SQLite 연결
        - row_factory 설정 (딕셔너리 스타일)
        """

    def get_previous_notams(self, data_source: str) -> Dict:
        """
        이전 NOTAM 데이터 조회
        - notam_records 테이블에서 읽기
        - {notam_no: notam_data} 딕셔너리 반환
        """

    def detect_changes(self, current_notams: List, data_source: str) -> Dict:
        """
        변경사항 감지
        1. 신규 NOTAM (이전에 없던 것)
        2. 업데이트 NOTAM (필드 변경)
        3. 삭제 NOTAM (현재에 없는 것)

        반환: {
            'new': [...],
            'updated': [...],
            'deleted': [...],
            'unchanged': count
        }
        """

    def compare_notams(self, previous: Dict, current: Dict) -> Dict:
        """
        두 NOTAM 비교
        - 필드별 비교 (issue_time, qcode, start_time 등)
        - 변경된 필드만 반환
        - {field: {previous: ..., current: ...}}
        """

    def save_change_log(self, notam_no, location, change_type,
                       change_details, ...) -> int:
        """
        변경 로그 저장
        - change_logs 테이블에 INSERT
        - change_details를 JSON으로 저장
        - 로그 ID 반환
        """

    def process_changes(self, changes: Dict, data_source: str) -> Dict:
        """
        변경사항 처리
        - 각 변경 유형별로 로그 저장
        - NEW, UPDATE, DELETE
        - 저장 개수 반환
        """

    def get_change_history(self, notam_no=None, location=None,
                          change_type=None, limit=100) -> List:
        """
        변경 이력 조회
        - 필터링 지원
        - 최신 순 정렬
        - JSON 파싱
        """

    def get_change_stats(self, data_source=None, hours=24) -> Dict:
        """
        변경 통계 조회
        - 기간별 필터
        - 소스별 필터
        - 변경 유형별 카운트
        """
```

**사용 예제**:
```python
from notam_change_detector import NOTAMChangeDetector

detector = NOTAMChangeDetector()

# 현재 NOTAM 리스트 (크롤링 결과)
current_notams = [...]  # List[Dict]

# 변경 감지
changes = detector.detect_changes(current_notams, 'domestic')

print(f"신규: {len(changes['new'])}개")
print(f"업데이트: {len(changes['updated'])}개")
print(f"삭제: {len(changes['deleted'])}개")

# 변경 로그 저장
result = detector.process_changes(changes, 'domestic')

# 통계 조회
stats = detector.get_change_stats('domestic', hours=24)
print(stats)  # {'NEW': 5, 'UPDATE': 3, 'DELETE': 1}

detector.close()
```

**변경 감지 로직**:
```
Previous NOTAM: {A1, A2, A3, A4}
Current NOTAM:  {A2, A3, A4, A5}

┌──────────┐
│ Compare  │
└────┬─────┘
     │
┌────▼─────────────────────────┐
│                              │
│ A1: 이전에만 존재 → DELETE   │
│ A2: 둘 다 존재 → 필드 비교    │
│     - 변경 있음 → UPDATE     │
│     - 변경 없음 → UNCHANGED  │
│ A3: 둘 다 존재 → UNCHANGED   │
│ A4: 둘 다 존재 → UNCHANGED   │
│ A5: 현재만 존재 → NEW        │
│                              │
└──────────────────────────────┘

결과:
- NEW: [A5]
- UPDATE: [A2]
- DELETE: [A1]
- UNCHANGED: 2 (A3, A4)
```

**장점**:
- 🔍 자동 변경 감지
- 📝 완전한 감사 추적
- 📊 통계 및 분석
- 🗄️ 영구 저장

---

#### `notam_monitor.py` (320줄)
**역할**: 크롤링 + 변경 감지 통합 모니터링 시스템 (권장)

**주요 클래스 및 메서드**:
```python
class NOTAMMonitor:
    def __init__(self, db_name='notam_realtime.db'):
        """
        초기화
        - 크롤러: lazy loading
        - 변경 감지기: lazy loading
        """

    def _init_crawler(self):
        """하이브리드 크롤러 초기화"""

    def _init_detector(self):
        """변경 감지기 초기화"""

    def monitor_single(self, data_source: str, hours_back: int,
                      enable_change_detection: bool = True) -> Dict:
        """
        단일 소스 모니터링
        1. 크롤링 실행
        2. 변경 감지 (옵션)
        3. 변경 로그 저장
        4. 결과 반환
        """

    def _get_current_notams(self, data_source: str):
        """현재 DB의 NOTAM 데이터 조회"""

    def monitor_all(self, hours_back: int = 24,
                   enable_change_detection: bool = True) -> Dict:
        """
        전체 모니터링 (국내 + 국제)
        - 순차 실행
        - 통합 결과 및 통계
        """

    def get_statistics(self, hours: int = 24) -> Dict:
        """
        통계 조회
        - 국내/국제 별도
        - 변경 유형별 카운트
        """
```

**사용 예제**:
```python
from notam_monitor import NOTAMMonitor

monitor = NOTAMMonitor()

# 전체 모니터링 (변경 감지 포함)
results = monitor.monitor_all(
    hours_back=24,
    enable_change_detection=True
)

# 결과 확인
domestic = results['domestic']
print(f"상태: {domestic['status']}")
print(f"크롤링: {domestic['crawl_result']['records_found']}개")

if domestic.get('change_result'):
    ch = domestic['change_result']
    print(f"신규: {ch['new']}, 업데이트: {ch['updated']}")

# 통계 조회
stats = monitor.get_statistics(hours=24)
print(f"국내 통계: {stats['domestic']}")
print(f"국제 통계: {stats['international']}")

monitor.close()
```

**프로세스 흐름**:
```
┌──────────────┐
│  Start       │
│  Monitor     │
└──────┬───────┘
       │
┌──────▼───────┐
│   Crawl      │ ← 하이브리드 크롤링
│   NOTAM      │
└──────┬───────┘
       │
    Success?
    ┌──┴──┐
   Yes    No
    │     │
    │     └──→ Return Error
    │
┌───▼────────┐
│  Get       │
│  Current   │
│  NOTAM     │
└───┬────────┘
    │
┌───▼────────┐
│  Detect    │
│  Changes   │
└───┬────────┘
    │
┌───▼────────┐
│  Save      │
│  Change    │
│  Logs      │
└───┬────────┘
    │
┌───▼────────┐
│  Return    │
│  Results   │
└────────────┘
```

**장점**:
- 🎯 올인원 솔루션
- 🔄 자동화 지원
- 📊 통합 결과
- 🚀 프로덕션 권장

---

### 3. 데이터베이스 모듈

#### `database.py` (750줄)
**역할**: 엔터프라이즈급 데이터베이스 관리 시스템

**주요 클래스 및 메서드**:
```python
class DatabaseManager:
    def __init__(self, db_type='auto', connection_string=None):
        """
        초기화
        - db_type: 'auto', 'sqlite', 'postgresql'
        - 환경변수 지원
        - 자동 연결
        """

    def _determine_db_type(db_type: str) -> str:
        """데이터베이스 타입 결정 (환경변수 체크)"""

    def _get_connection_string() -> str:
        """연결 문자열 가져오기 (환경변수)"""

    def _connect(self):
        """데이터베이스 연결"""

    def create_tables(self, schema_file=None) -> bool:
        """
        테이블 생성
        - PostgreSQL: schema.sql
        - SQLite: schema_sqlite.sql
        """

    def seed_airports(self, seed_file=None) -> bool:
        """공항 초기 데이터 로드 (18개)"""

    def save_notam(self, notam_data, crawl_batch_id=None) -> int:
        """
        NOTAM 저장/업데이트
        - ON CONFLICT (PostgreSQL)
        - INSERT OR REPLACE (SQLite)
        - JSON 필드 자동 변환
        """

    def get_notam(self, notam_no, location) -> Dict:
        """단일 NOTAM 조회"""

    def get_active_notams(self, location=None, limit=100) -> List:
        """활성 NOTAM 목록 조회"""

    def save_notam_change(self, ...):
        """NOTAM 변경 이력 저장"""

    def create_crawl_batch(self, data_source: str) -> int:
        """크롤링 배치 시작"""

    def update_crawl_batch(self, batch_id, status, ...):
        """크롤링 배치 업데이트"""

    def get_airport_id(self, code: str) -> int:
        """공항 ID 조회"""

    def get_notam_changes(self, notam_no=None, location=None,
                         limit=100) -> List:
        """변경 이력 조회"""

    def get_crawl_stats(self, data_source=None, days=7) -> List:
        """크롤링 통계"""
```

**사용 예제**:
```python
from database import DatabaseManager

# SQLite (개발)
db = DatabaseManager(db_type='sqlite')

# PostgreSQL (프로덕션)
db = DatabaseManager(
    db_type='postgresql',
    connection_string='postgresql://user:pass@localhost/notam_db'
)

# 테이블 생성
db.create_tables()

# 공항 데이터 로드
db.seed_airports()

# NOTAM 저장
notam = {
    'notam_no': 'A1234/25',
    'location': 'RKSI',
    'notam_type': 'A',
    'status': 'ACTIVE',
    'issue_time': '2025-11-10T14:30:00',
    'start_time': '2025-11-10T15:00:00',
    'end_time': '2025-11-10T18:00:00',
    'qcode': 'QWLC',
    'full_text': 'Runway 33L/15R closed...',
    'parsed_data': {'severity': 'HIGH'}
}

notam_id = db.save_notam(notam)
print(f"NOTAM ID: {notam_id}")

# 조회
notam = db.get_notam('A1234/25', 'RKSI')
active_notams = db.get_active_notams('RKSI', limit=50)

db.close()
```

**환경변수 설정**:
```bash
# SQLite
export NOTAM_DB_TYPE=sqlite
export NOTAM_SQLITE_PATH=./notam_realtime.db

# PostgreSQL
export NOTAM_DB_TYPE=postgresql
export NOTAM_DATABASE_URL=postgresql://user:pass@localhost:5432/notam_db
```

---

#### `database/schema.sql` (219줄)
**역할**: PostgreSQL 완전 스키마 (프로덕션용)

**포함 요소**:
- ✅ 4개 테이블 (airports, notams, notam_changes, crawl_batches)
- ✅ 17개 인덱스 (성능 최적화)
- ✅ 3개 뷰 (편의 기능)
- ✅ 2개 트리거 함수 (자동 감사)

**주요 테이블**:

1. **airports** (공항 마스터)
```sql
CREATE TABLE airports (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name_kr VARCHAR(100),
    name_en VARCHAR(100),
    icao_code VARCHAR(10),
    iata_code VARCHAR(10),
    country VARCHAR(50) DEFAULT 'KR',
    is_domestic BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

2. **notams** (NOTAM 마스터)
```sql
CREATE TABLE notams (
    id SERIAL PRIMARY KEY,
    airport_id INTEGER REFERENCES airports(id) ON DELETE CASCADE,
    notam_no VARCHAR(50) NOT NULL,
    location VARCHAR(10) NOT NULL,
    notam_type VARCHAR(20),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    issue_time TIMESTAMP,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    qcode VARCHAR(10),
    full_text TEXT,
    raw_data JSONB,
    parsed_data JSONB,
    data_source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_notam UNIQUE (notam_no, location)
);
```

3. **notam_changes** (변경 이력)
```sql
CREATE TABLE notam_changes (
    id SERIAL PRIMARY KEY,
    notam_id INTEGER REFERENCES notams(id) ON DELETE CASCADE,
    notam_no VARCHAR(50) NOT NULL,
    location VARCHAR(10) NOT NULL,
    change_type VARCHAR(20) NOT NULL,
    previous_status VARCHAR(20),
    new_status VARCHAR(20),
    previous_data JSONB,
    new_data JSONB,
    change_details JSONB,
    crawler_batch_id INTEGER REFERENCES crawl_batches(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

4. **crawl_batches** (크롤링 배치)
```sql
CREATE TABLE crawl_batches (
    id SERIAL PRIMARY KEY,
    data_source VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'RUNNING',
    batch_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_records INTEGER DEFAULT 0,
    new_records INTEGER DEFAULT 0,
    updated_records INTEGER DEFAULT 0,
    skipped_records INTEGER DEFAULT 0,
    error_message TEXT,
    execution_time_seconds NUMERIC(10, 3),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

**인덱스 전략**:
```sql
-- 단일 열 인덱스
CREATE INDEX idx_notams_location ON notams(location);
CREATE INDEX idx_notams_status ON notams(status);
CREATE INDEX idx_notams_issue_time ON notams(issue_time DESC);
CREATE INDEX idx_notams_start_time ON notams(start_time DESC);
CREATE INDEX idx_notams_end_time ON notams(end_time DESC);

-- 복합 인덱스 (쿼리 최적화)
CREATE INDEX idx_notams_status_location ON notams(status, location);
CREATE INDEX idx_notams_status_issue_time ON notams(status, issue_time DESC);

-- 변경 이력 인덱스
CREATE INDEX idx_changes_notam_no ON notam_changes(notam_no);
CREATE INDEX idx_changes_location ON notam_changes(location);
CREATE INDEX idx_changes_created_at ON notam_changes(created_at DESC);
```

**트리거** (자동 변경 감지):
```sql
-- updated_at 자동 갱신
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_notams_updated_at
BEFORE UPDATE ON notams
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

#### `database/schema_sqlite.sql` (104줄)
**역할**: SQLite 호환 스키마 (개발/테스트용)

**PostgreSQL과의 차이점**:
- SERIAL → INTEGER PRIMARY KEY AUTOINCREMENT
- JSONB → TEXT (JSON 문자열)
- TIMESTAMP → TEXT (ISO 8601 형식)
- ON DELETE CASCADE → 지원
- 트리거 함수 → 제거 (애플리케이션 레벨 처리)

---

#### `database/seed_airports.sql` (45줄)
**역할**: 공항 초기 데이터 (18개 한국 공항)

```sql
INSERT INTO airports (code, name_kr, name_en, icao_code, iata_code, is_domestic, is_active)
VALUES
('RKSI', '인천국제공항', 'Incheon International Airport', 'RKSI', 'ICN', false, true),
('RKSS', '서울/김포공항', 'Seoul/Gimpo Airport', 'RKSS', 'GMP', true, true),
('RKPK', '부산/김해공항', 'Busan/Gimhae Airport', 'RKPK', 'PUS', true, true),
-- ... 15개 더
```

---

### 4. 테스트 파일

#### `test_hybrid.py`
하이브리드 크롤러 테스트 (API 모드)

#### `test_monitor_simple.py`
통합 모니터링 시스템 테스트 (변경 감지 비활성화)

#### `test_api_24h.py`
API 크롤러 24시간 범위 테스트

#### `test_api_direct.py`
API 직접 호출 테스트 (Raw 응답 확인)

#### `test_notam_crawler.py` (기존)
Selenium 크롤러 테스트

---

### 5. 문서 파일

#### `README.md`
간략한 프로젝트 소개 및 빠른 시작 가이드

#### `PROJECT_README.md` (이 파일)
전체 프로젝트 상세 문서

#### `DATABASE_SCHEMA_README.md`
데이터베이스 스키마 상세 문서

#### `IMPLEMENTATION_SUMMARY.md`
Phase 1 구현 요약

---

## 💻 설치 및 환경 설정

### 시스템 요구사항

- **운영체제**: Windows 10/11, Linux, macOS
- **Python**: 3.8 이상
- **메모리**: 최소 2GB RAM
- **디스크**: 최소 500MB 여유 공간
- **Chrome**: Selenium 사용 시 필요

### Python 패키지 설치

```bash
# 필수 패키지
pip install requests
pip install pytz

# Selenium 사용 시 (백업용)
pip install selenium

# PostgreSQL 사용 시 (프로덕션)
pip install psycopg2-binary
```

또는 requirements.txt 사용:
```bash
pip install -r requirements.txt
```

**requirements.txt**:
```
requests>=2.31.0
pytz>=2023.3
selenium>=4.15.0
psycopg2-binary>=2.9.9  # PostgreSQL 사용 시
```

### Chrome 드라이버 설치 (Selenium 사용 시)

1. Chrome 버전 확인:
```bash
# Windows
chrome://version

# Linux
google-chrome --version
```

2. 드라이버 다운로드:
- https://chromedriver.chromium.org/downloads
- Chrome 버전과 일치하는 드라이버 선택

3. PATH에 추가:
```bash
# Linux/macOS
sudo mv chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver

# Windows
# 시스템 환경변수 PATH에 추가
```

### 데이터베이스 설정

#### SQLite (개발/테스트)
```bash
# 자동으로 생성됨
# 별도 설정 불필요
```

#### PostgreSQL (프로덕션)

1. PostgreSQL 설치:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# Windows
# https://www.postgresql.org/download/windows/
```

2. 데이터베이스 생성:
```bash
sudo -u postgres psql

CREATE DATABASE notam_db;
CREATE USER notam_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE notam_db TO notam_user;
\q
```

3. 환경변수 설정:
```bash
export NOTAM_DB_TYPE=postgresql
export NOTAM_DATABASE_URL=postgresql://notam_user:your_password@localhost:5432/notam_db
```

4. 테이블 생성:
```python
from database import DatabaseManager

db = DatabaseManager(db_type='postgresql')
db.create_tables()
db.seed_airports()
db.close()
```

---

## 🚀 사용 방법

### 1. 기본 크롤링

#### API 크롤러 (권장)
```python
from notam_crawler_api import NOTAMCrawlerAPI

crawler = NOTAMCrawlerAPI()

# 국내 NOTAM (최근 24시간)
result = crawler.crawl_notam_api('domestic', hours_back=24)

print(f"발견: {result['records_found']}개")
print(f"저장: {result['records_saved']}개")
print(f"시간: {result['execution_time']:.2f}초")

crawler.close()
```

#### 하이브리드 크롤러 (프로덕션 권장)
```python
from notam_hybrid_crawler import NOTAMHybridCrawler

crawler = NOTAMHybridCrawler()

# 전체 크롤링 (국내 + 국제)
results = crawler.crawl_all(hours_back=24)

# 결과 확인
for source in ['domestic', 'international']:
    result = results[source]
    print(f"\n{source.upper()}:")
    print(f"  발견: {result['records_found']}개")
    print(f"  방법: {result['method']}")  # API or SELENIUM
    print(f"  시간: {result['execution_time']:.2f}초")

crawler.close()
```

### 2. 변경 감지

#### 기본 변경 감지
```python
from notam_change_detector import NOTAMChangeDetector
import sqlite3

detector = NOTAMChangeDetector()

# 현재 NOTAM 가져오기
conn = sqlite3.connect('notam_realtime.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM notam_records WHERE data_source = 'domestic'")
current_notams = [dict(row) for row in cursor.fetchall()]
conn.close()

# 변경 감지
changes = detector.detect_changes(current_notams, 'domestic')

print(f"신규: {len(changes['new'])}개")
print(f"업데이트: {len(changes['updated'])}개")
print(f"삭제: {len(changes['deleted'])}개")

# 변경 로그 저장
result = detector.process_changes(changes, 'domestic')
print(f"로그 저장: {result['saved_count']}개")

# 통계 조회
stats = detector.get_change_stats('domestic', hours=24)
print(f"통계: {stats}")

detector.close()
```

### 3. 통합 모니터링 (권장)

#### 전체 모니터링
```python
from notam_monitor import NOTAMMonitor

monitor = NOTAMMonitor()

# 전체 모니터링 (변경 감지 포함)
results = monitor.monitor_all(
    hours_back=24,
    enable_change_detection=True
)

# 결과 출력
for source in ['domestic', 'international']:
    result = results[source]

    print(f"\n{source.upper()}:")
    print(f"  상태: {result['status']}")

    # 크롤링 결과
    if result.get('crawl_result'):
        cr = result['crawl_result']
        print(f"  크롤링: {cr['records_found']}개 (방법: {cr['method']})")

    # 변경 결과
    if result.get('change_result'):
        ch = result['change_result']
        print(f"  변경: 신규 {ch['new']}, 업데이트 {ch['updated']}, 삭제 {ch['deleted']}")

# 통계 조회
stats = monitor.get_statistics(hours=24)
print(f"\n통계:")
print(f"  국내: {stats['domestic']}")
print(f"  국제: {stats['international']}")

monitor.close()
```

#### 단일 소스 모니터링
```python
from notam_monitor import NOTAMMonitor

monitor = NOTAMMonitor()

# 국내만 모니터링 (변경 감지 비활성화)
result = monitor.monitor_single(
    data_source='domestic',
    hours_back=24,
    enable_change_detection=False
)

print(f"상태: {result['status']}")
print(f"발견: {result['crawl_result']['records_found']}개")

monitor.close()
```

### 4. 실시간 모니터링 스크립트

**continuous_monitor.py**:
```python
#!/usr/bin/env python
"""
NOTAM 실시간 모니터링 - 5분마다 실행
"""
from notam_monitor import NOTAMMonitor
import time
from datetime import datetime

def main():
    monitor = NOTAMMonitor()

    print("NOTAM 실시간 모니터링 시작")
    print("Ctrl+C로 중단")
    print("="*70)

    try:
        while True:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 모니터링 실행...")

            # 전체 모니터링 (최근 1시간)
            results = monitor.monitor_all(
                hours_back=1,
                enable_change_detection=True
            )

            # 변경사항 알림
            for source in ['domestic', 'international']:
                result = results[source]

                if result.get('change_result'):
                    ch = result['change_result']

                    if ch['new'] > 0 or ch['updated'] > 0 or ch['deleted'] > 0:
                        print(f"\n⚠️  {source.upper()} NOTAM 변경 감지!")
                        print(f"   신규: {ch['new']}, 업데이트: {ch['updated']}, 삭제: {ch['deleted']}")

                        # 여기에 알림 로직 추가
                        # - 이메일 발송
                        # - Slack 메시지
                        # - 웹훅 호출

            print(f"다음 실행: 5분 후")
            time.sleep(300)  # 5분 대기

    except KeyboardInterrupt:
        print("\n\n모니터링 중단됨")

    finally:
        monitor.close()

if __name__ == '__main__':
    main()
```

실행:
```bash
python continuous_monitor.py
```

### 5. 크론잡 설정 (자동 스케줄링)

#### Linux/macOS

```bash
# crontab 편집
crontab -e

# 매 5분마다 실행
*/5 * * * * cd /path/to/code && python notam_monitor.py >> /var/log/notam.log 2>&1

# 매 시간 실행 (정각)
0 * * * * cd /path/to/code && python notam_monitor.py >> /var/log/notam.log 2>&1

# 매일 오전 9시 실행
0 9 * * * cd /path/to/code && python notam_monitor.py >> /var/log/notam.log 2>&1
```

#### Windows 작업 스케줄러

1. 작업 스케줄러 실행 (`taskschd.msc`)
2. 작업 만들기:
   - **이름**: NOTAM Monitor
   - **트리거**: 5분마다 반복
   - **동작**: 프로그램 시작
   - **프로그램**: `python`
   - **인수**: `C:\Users\allof\Desktop\code\notam_monitor.py`
   - **시작 위치**: `C:\Users\allof\Desktop\code`

---

## 🗄️ 데이터베이스 스키마

### 테이블 관계도

```
┌─────────────┐
│  airports   │
│             │
│ - id (PK)   │
│ - code      │
│ - name_kr   │
│ - name_en   │
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────────────────────┐
│  notams                     │
│                             │
│ - id (PK)                   │
│ - airport_id (FK)           │
│ - notam_no                  │
│ - location                  │
│ - notam_type                │
│ - status                    │
│ - issue_time                │
│ - start_time                │
│ - end_time                  │
│ - qcode                     │
│ - full_text                 │
│ - raw_data (JSON)           │
│ - parsed_data (JSON)        │
│ UNIQUE(notam_no, location)  │
└──────┬──────────────────────┘
       │
       │ 1:N
       │
┌──────▼────────────────────┐
│  notam_changes            │
│                           │
│ - id (PK)                 │
│ - notam_id (FK)           │
│ - notam_no                │
│ - location                │
│ - change_type             │
│ - previous_status         │
│ - new_status              │
│ - previous_data (JSON)    │
│ - new_data (JSON)         │
│ - change_details (JSON)   │
│ - created_at              │
└───────────────────────────┘

┌────────────────────────┐
│  crawl_batches         │
│                        │
│ - id (PK)              │
│ - data_source          │
│ - status               │
│ - batch_timestamp      │
│ - total_records        │
│ - new_records          │
│ - updated_records      │
│ - skipped_records      │
│ - error_message        │
│ - execution_time       │
└────────────────────────┘

┌────────────────────────┐
│  change_logs           │
│  (변경 감지용)          │
│                        │
│ - id (PK)              │
│ - timestamp            │
│ - notam_no             │
│ - location             │
│ - data_source          │
│ - change_type          │
│ - change_details (JSON)│
└────────────────────────┘
```

### 주요 쿼리 예제

#### 1. 활성 NOTAM 조회
```sql
SELECT * FROM notam_records
WHERE data_source = 'domestic'
  AND datetime(start_time) <= datetime('now')
  AND (datetime(end_time) >= datetime('now') OR end_time IS NULL)
ORDER BY issue_time DESC
LIMIT 100;
```

#### 2. 특정 공항 NOTAM
```sql
SELECT * FROM notam_records
WHERE location = 'RKSI'
  AND data_source = 'domestic'
ORDER BY issue_time DESC;
```

#### 3. 최근 변경 이력
```sql
SELECT * FROM change_logs
WHERE data_source = 'domestic'
  AND datetime(timestamp) >= datetime('now', '-24 hours')
ORDER BY timestamp DESC;
```

#### 4. 변경 통계
```sql
SELECT
    change_type,
    COUNT(*) as count
FROM change_logs
WHERE data_source = 'domestic'
  AND datetime(timestamp) >= datetime('now', '-24 hours')
GROUP BY change_type;
```

#### 5. 크롤링 성공률
```sql
SELECT
    data_source,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success,
    ROUND(100.0 * SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM crawl_logs
WHERE datetime(crawl_timestamp) >= datetime('now', '-7 days')
GROUP BY data_source;
```

---

## 🔜 향후 작업 (Phase 3-5)

### Phase 3: REST API 서버 구축 (사용자 작업)

#### 목표
Flask 또는 FastAPI 기반 REST API 서버 구축

#### 필요 패키지
```bash
pip install flask flask-cors
# 또는
pip install fastapi uvicorn
```

#### 엔드포인트 설계

**1. GET /api/notams**
- 설명: NOTAM 목록 조회
- 쿼리 파라미터:
  - `data_source`: domestic/international
  - `location`: 공항 코드 (RKSI, RKSS 등)
  - `status`: ACTIVE/CANCELLED
  - `limit`: 최대 개수 (기본: 100)
  - `offset`: 페이지네이션
- 응답:
```json
{
  "status": "success",
  "total": 150,
  "count": 100,
  "data": [
    {
      "notam_no": "A1234/25",
      "location": "RKSI",
      "notam_type": "A",
      "status": "ACTIVE",
      "issue_time": "2025-11-10T14:30:00",
      "start_time": "2025-11-10T15:00:00",
      "end_time": "2025-11-10T18:00:00",
      "qcode": "QWLC",
      "full_text": "Runway 33L/15R closed..."
    }
  ]
}
```

**2. GET /api/notams/{notam_no}**
- 설명: 특정 NOTAM 조회
- 경로 파라미터:
  - `notam_no`: NOTAM 번호
- 쿼리 파라미터:
  - `location`: 공항 코드
- 응답:
```json
{
  "status": "success",
  "data": {
    "notam_no": "A1234/25",
    "location": "RKSI",
    ...
  }
}
```

**3. GET /api/changes**
- 설명: 변경 이력 조회
- 쿼리 파라미터:
  - `data_source`: domestic/international
  - `notam_no`: NOTAM 번호 (선택)
  - `location`: 공항 코드 (선택)
  - `change_type`: NEW/UPDATE/DELETE (선택)
  - `hours`: 최근 몇 시간 (기본: 24)
  - `limit`: 최대 개수 (기본: 100)
- 응답:
```json
{
  "status": "success",
  "total": 50,
  "count": 50,
  "data": [
    {
      "id": 123,
      "timestamp": "2025-11-10T14:30:00",
      "notam_no": "A1234/25",
      "location": "RKSI",
      "change_type": "NEW",
      "change_details": {...}
    }
  ]
}
```

**4. GET /api/stats**
- 설명: 통계 조회
- 쿼리 파라미터:
  - `data_source`: domestic/international/all
  - `hours`: 최근 몇 시간 (기본: 24)
- 응답:
```json
{
  "status": "success",
  "period_hours": 24,
  "data": {
    "domestic": {
      "total_notams": 150,
      "active_notams": 120,
      "changes": {
        "NEW": 10,
        "UPDATE": 5,
        "DELETE": 3
      },
      "crawl_stats": {
        "total_crawls": 288,
        "successful_crawls": 287,
        "success_rate": 99.65
      }
    },
    "international": {...}
  }
}
```

**5. POST /api/crawl**
- 설명: 수동 크롤링 트리거
- 요청 본문:
```json
{
  "data_source": "domestic",
  "hours_back": 24,
  "enable_change_detection": true
}
```
- 응답:
```json
{
  "status": "success",
  "message": "Crawling started",
  "result": {
    "records_found": 8,
    "records_saved": 8,
    "execution_time": 0.25,
    "changes": {
      "new": 2,
      "updated": 1,
      "deleted": 0
    }
  }
}
```

**6. GET /api/health**
- 설명: 헬스 체크
- 응답:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T14:30:00",
  "database": "connected",
  "last_crawl": {
    "domestic": "2025-11-10T14:25:00",
    "international": "2025-11-10T14:25:30"
  }
}
```

#### Flask 구현 예제

**app.py**:
```python
from flask import Flask, jsonify, request
from flask_cors import CORS
from notam_monitor import NOTAMMonitor
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)  # CORS 활성화

monitor = NOTAMMonitor()

@app.route('/api/notams', methods=['GET'])
def get_notams():
    """NOTAM 목록 조회"""
    data_source = request.args.get('data_source', 'domestic')
    location = request.args.get('location')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))

    conn = sqlite3.connect('notam_realtime.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM notam_records WHERE data_source = ?"
    params = [data_source]

    if location:
        query += " AND location = ?"
        params.append(location)

    query += " ORDER BY issue_time DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    notams = [dict(row) for row in cursor.fetchall()]

    # 전체 개수
    count_query = "SELECT COUNT(*) FROM notam_records WHERE data_source = ?"
    count_params = [data_source]
    if location:
        count_query += " AND location = ?"
        count_params.append(location)

    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        'status': 'success',
        'total': total,
        'count': len(notams),
        'data': notams
    })

@app.route('/api/notams/<notam_no>', methods=['GET'])
def get_notam(notam_no):
    """특정 NOTAM 조회"""
    location = request.args.get('location')

    if not location:
        return jsonify({
            'status': 'error',
            'message': 'location parameter required'
        }), 400

    conn = sqlite3.connect('notam_realtime.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM notam_records WHERE notam_no = ? AND location = ?",
        (notam_no, location)
    )

    notam = cursor.fetchone()
    conn.close()

    if notam:
        return jsonify({
            'status': 'success',
            'data': dict(notam)
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'NOTAM not found'
        }), 404

@app.route('/api/changes', methods=['GET'])
def get_changes():
    """변경 이력 조회"""
    data_source = request.args.get('data_source', 'domestic')
    hours = int(request.args.get('hours', 24))
    limit = int(request.args.get('limit', 100))

    from notam_change_detector import NOTAMChangeDetector
    detector = NOTAMChangeDetector()

    # 변경 이력 조회 (시간 필터 추가 필요)
    conn = sqlite3.connect('notam_realtime.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM change_logs
        WHERE data_source = ?
          AND datetime(timestamp) >= datetime('now', ? || ' hours')
        ORDER BY timestamp DESC
        LIMIT ?
    """, (data_source, -hours, limit))

    changes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    detector.close()

    return jsonify({
        'status': 'success',
        'total': len(changes),
        'count': len(changes),
        'data': changes
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """통계 조회"""
    hours = int(request.args.get('hours', 24))

    stats = monitor.get_statistics(hours=hours)

    return jsonify({
        'status': 'success',
        'period_hours': hours,
        'data': stats
    })

@app.route('/api/crawl', methods=['POST'])
def trigger_crawl():
    """수동 크롤링 트리거"""
    data = request.get_json()

    data_source = data.get('data_source', 'domestic')
    hours_back = data.get('hours_back', 24)
    enable_change_detection = data.get('enable_change_detection', True)

    result = monitor.monitor_single(
        data_source=data_source,
        hours_back=hours_back,
        enable_change_detection=enable_change_detection
    )

    if result['status'] == 'SUCCESS':
        response = {
            'status': 'success',
            'message': 'Crawling completed',
            'result': {
                'records_found': result['crawl_result']['records_found'],
                'records_saved': result['crawl_result']['records_saved'],
                'execution_time': result['crawl_result']['execution_time'],
                'method': result['crawl_result']['method']
            }
        }

        if result.get('change_result'):
            response['result']['changes'] = {
                'new': result['change_result']['new'],
                'updated': result['change_result']['updated'],
                'deleted': result['change_result']['deleted']
            }

        return jsonify(response)
    else:
        return jsonify({
            'status': 'error',
            'message': 'Crawling failed',
            'error': result.get('error', 'Unknown error')
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    conn = sqlite3.connect('notam_realtime.db')
    cursor = conn.cursor()

    # 마지막 크롤링 시간
    cursor.execute("""
        SELECT data_source, MAX(crawl_timestamp) as last_crawl
        FROM crawl_logs
        GROUP BY data_source
    """)

    last_crawls = {}
    for row in cursor.fetchall():
        last_crawls[row[0]] = row[1]

    conn.close()

    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected',
        'last_crawl': last_crawls
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

실행:
```bash
python app.py
```

테스트:
```bash
# NOTAM 목록 조회
curl http://localhost:5000/api/notams?data_source=domestic&limit=10

# 특정 NOTAM 조회
curl http://localhost:5000/api/notams/A1234/25?location=RKSI

# 변경 이력
curl http://localhost:5000/api/changes?data_source=domestic&hours=24

# 통계
curl http://localhost:5000/api/stats?hours=24

# 수동 크롤링
curl -X POST http://localhost:5000/api/crawl \
  -H "Content-Type: application/json" \
  -d '{"data_source": "domestic", "hours_back": 24}'

# 헬스 체크
curl http://localhost:5000/api/health
```

---

### Phase 4: AWS 배포 (사용자 작업)

#### 목표
AWS 클라우드에 프로덕션 환경 구축

#### 아키텍처 옵션

**옵션 1: EC2 + RDS (간단한 배포)**
```
┌─────────────────────────────────┐
│         Internet                │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│      Application Load           │
│      Balancer (ALB)             │
└────────────┬────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼──────┐   ┌──────▼───┐
│ EC2      │   │ EC2      │
│ Instance │   │ Instance │
│ (Flask)  │   │ (Flask)  │
└───┬──────┘   └──────┬───┘
    │                 │
    └────────┬────────┘
             │
┌────────────▼────────────────────┐
│      RDS PostgreSQL             │
│      (Multi-AZ)                 │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│   CloudWatch Events             │
│   (Cron: */5 * * * *)           │
└─────────────────────────────────┘
```

**옵션 2: Lambda + RDS (서버리스)**
```
┌─────────────────────────────────┐
│         Internet                │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│      API Gateway                │
│      (REST API)                 │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│      Lambda Functions           │
│  - get_notams                   │
│  - get_changes                  │
│  - get_stats                    │
│  - trigger_crawl                │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│      RDS PostgreSQL             │
│      (Serverless v2)            │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│   EventBridge                   │
│   (Cron: rate(5 minutes))       │
│         │                       │
│   ┌─────▼─────┐                 │
│   │  Lambda   │                 │
│   │ (Monitor) │                 │
│   └───────────┘                 │
└─────────────────────────────────┘
```

#### 단계별 배포 가이드

**1. RDS PostgreSQL 설정**

```bash
# AWS CLI 사용
aws rds create-db-instance \
  --db-instance-identifier notam-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username notam_admin \
  --master-user-password YourStrongPassword \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxxxxx \
  --db-subnet-group-name default \
  --backup-retention-period 7 \
  --multi-az \
  --publicly-accessible false
```

**2. EC2 인스턴스 설정**

```bash
# 1. EC2 인스턴스 생성 (Ubuntu 22.04)
# 2. SSH 접속
ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com

# 3. 패키지 업데이트
sudo apt-get update
sudo apt-get upgrade -y

# 4. Python 및 pip 설치
sudo apt-get install python3 python3-pip -y

# 5. Chrome 및 드라이버 설치 (Selenium 백업용)
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f -y

# 6. 프로젝트 클론/업로드
scp -i your-key.pem -r /path/to/code ubuntu@ec2:~/

# 7. Python 패키지 설치
cd ~/code
pip3 install -r requirements.txt

# 8. 환경변수 설정
cat >> ~/.bashrc <<EOF
export NOTAM_DB_TYPE=postgresql
export NOTAM_DATABASE_URL=postgresql://notam_admin:password@your-rds-endpoint:5432/notam_db
EOF
source ~/.bashrc

# 9. 테이블 생성
python3 -c "
from database import DatabaseManager
db = DatabaseManager(db_type='postgresql')
db.create_tables()
db.seed_airports()
db.close()
"

# 10. Flask 앱 실행 (테스트)
python3 app.py

# 11. Gunicorn으로 배포 (프로덕션)
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**3. Systemd 서비스 설정 (자동 시작)**

**/etc/systemd/system/notam-api.service**:
```ini
[Unit]
Description=NOTAM API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/code
Environment="NOTAM_DB_TYPE=postgresql"
Environment="NOTAM_DATABASE_URL=postgresql://notam_admin:password@your-rds:5432/notam_db"
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

활성화:
```bash
sudo systemctl daemon-reload
sudo systemctl enable notam-api
sudo systemctl start notam-api
sudo systemctl status notam-api
```

**4. 크론잡 설정 (자동 모니터링)**

```bash
# crontab 편집
crontab -e

# 매 5분마다 크롤링
*/5 * * * * cd /home/ubuntu/code && /usr/bin/python3 notam_monitor.py >> /var/log/notam.log 2>&1
```

**5. Nginx 리버스 프록시 (옵션)**

```bash
# Nginx 설치
sudo apt-get install nginx -y

# 설정 파일
sudo nano /etc/nginx/sites-available/notam-api
```

**/etc/nginx/sites-available/notam-api**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

활성화:
```bash
sudo ln -s /etc/nginx/sites-available/notam-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**6. ALB 설정 (Auto Scaling)**

AWS 콘솔에서:
1. Application Load Balancer 생성
2. Target Group 생성 (EC2 인스턴스)
3. Health Check 설정: `/api/health`
4. Auto Scaling Group 생성
5. CloudWatch 알람 설정

**7. Lambda 배포 (서버리스 옵션)**

**lambda_handler.py**:
```python
import json
from notam_monitor import NOTAMMonitor

monitor = NOTAMMonitor()

def lambda_handler(event, context):
    """Lambda 함수 핸들러"""

    # 크롤링 실행
    results = monitor.monitor_all(
        hours_back=1,
        enable_change_detection=True
    )

    return {
        'statusCode': 200,
        'body': json.dumps(results, default=str)
    }
```

배포:
```bash
# 패키지 생성
mkdir lambda_package
pip install -r requirements.txt -t lambda_package/
cp *.py lambda_package/
cd lambda_package
zip -r ../lambda_function.zip .

# Lambda 함수 생성 (AWS CLI)
aws lambda create-function \
  --function-name notam-monitor \
  --runtime python3.9 \
  --role arn:aws:iam::123456789012:role/lambda-role \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://../lambda_function.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables="{NOTAM_DB_TYPE=postgresql,NOTAM_DATABASE_URL=postgresql://...}"
```

**8. EventBridge 스케줄 (Lambda 트리거)**

```bash
# CloudWatch Events Rule 생성
aws events put-rule \
  --name notam-monitor-schedule \
  --schedule-expression "rate(5 minutes)" \
  --state ENABLED

# Lambda 권한 부여
aws lambda add-permission \
  --function-name notam-monitor \
  --statement-id eventbridge-invoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:region:account:rule/notam-monitor-schedule

# Target 추가
aws events put-targets \
  --rule notam-monitor-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:region:account:function:notam-monitor"
```

---

### Phase 5: 모니터링 및 최적화 (향후 진행)

#### 목표
시스템 모니터링, 알림, 성능 최적화

#### 1. Prometheus + Grafana 모니터링

**필요 패키지**:
```bash
pip install prometheus-flask-exporter
```

**app.py 수정**:
```python
from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# 기본 메트릭 자동 수집
# - flask_http_request_duration_seconds
# - flask_http_request_total
# - flask_http_request_exceptions_total

# 커스텀 메트릭 추가
from prometheus_client import Counter, Gauge, Histogram

notam_crawl_total = Counter(
    'notam_crawl_total',
    'Total number of NOTAM crawls',
    ['data_source', 'status']
)

notam_current_count = Gauge(
    'notam_current_count',
    'Current number of active NOTAMs',
    ['data_source', 'location']
)

notam_crawl_duration = Histogram(
    'notam_crawl_duration_seconds',
    'NOTAM crawl duration in seconds',
    ['data_source']
)

@app.route('/api/crawl', methods=['POST'])
def trigger_crawl():
    with notam_crawl_duration.labels(data_source='domestic').time():
        result = monitor.monitor_single('domestic', 24, True)

        notam_crawl_total.labels(
            data_source='domestic',
            status=result['status']
        ).inc()

        # 현재 NOTAM 수 업데이트
        notam_current_count.labels(
            data_source='domestic',
            location='RKSI'
        ).set(result['crawl_result']['records_found'])

        return jsonify(result)

# /metrics 엔드포인트 자동 생성
```

**Grafana 대시보드**:
- NOTAM 크롤링 성공률
- 크롤링 실행 시간 (p50, p95, p99)
- 활성 NOTAM 수 (시간별 추이)
- 변경사항 빈도 (신규/업데이트/삭제)
- API 응답 시간
- 에러율

#### 2. 알림 시스템

**이메일 알림**:
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_alert(subject, body, recipients):
    """이메일 알림 발송"""
    sender = "notam-alert@yourdomain.com"
    password = "your_password"

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender, password)
    server.send_message(msg)
    server.quit()

# 사용 예
def check_critical_notams():
    """중요 NOTAM 확인 및 알림"""
    conn = sqlite3.connect('notam_realtime.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM notam_records
        WHERE qcode LIKE 'QA%'  -- 공항 폐쇄 관련
          AND status = 'ACTIVE'
          AND datetime(start_time) <= datetime('now')
          AND (datetime(end_time) >= datetime('now') OR end_time IS NULL)
    """)

    critical_notams = cursor.fetchall()
    conn.close()

    if critical_notams:
        subject = f"⚠️ 중요 NOTAM 알림 ({len(critical_notams)}건)"

        body = "<h2>중요 NOTAM 발생</h2><ul>"
        for notam in critical_notams:
            body += f"<li>{notam['notam_no']} - {notam['location']}: {notam['full_text']}</li>"
        body += "</ul>"

        send_email_alert(subject, body, ['admin@yourdomain.com'])
```

**Slack 알림**:
```python
import requests

def send_slack_alert(webhook_url, message):
    """Slack 웹훅 알림"""
    payload = {
        'text': message,
        'username': 'NOTAM Alert Bot',
        'icon_emoji': ':airplane:'
    }

    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200

# 사용 예
webhook_url = 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

changes = detector.detect_changes(current_notams, 'domestic')

if changes['new'] or changes['updated'] or changes['deleted']:
    message = f"""
🔔 *NOTAM 변경 감지*
• 신규: {len(changes['new'])}개
• 업데이트: {len(changes['updated'])}개
• 삭제: {len(changes['deleted'])}개
    """
    send_slack_alert(webhook_url, message)
```

#### 3. 성능 최적화

**캐싱 (Redis)**:
```bash
pip install redis
```

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@app.route('/api/notams', methods=['GET'])
def get_notams():
    cache_key = f"notams:{data_source}:{location}:{limit}"

    # 캐시 확인
    cached = redis_client.get(cache_key)
    if cached:
        return jsonify(json.loads(cached))

    # DB 조회
    notams = query_database()

    # 캐시 저장 (5분)
    redis_client.setex(cache_key, 300, json.dumps(notams))

    return jsonify(notams)
```

**데이터베이스 인덱스 추가**:
```sql
-- 복합 인덱스 (자주 사용하는 쿼리)
CREATE INDEX idx_notam_records_source_location_time
ON notam_records(data_source, location, issue_time DESC);

-- 부분 인덱스 (조건부)
CREATE INDEX idx_notam_records_active
ON notam_records(location, start_time)
WHERE status = 'ACTIVE';
```

**비동기 크롤링** (Python asyncio):
```python
import asyncio
import aiohttp

async def crawl_async(data_source):
    """비동기 크롤링"""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as response:
            return await response.json()

async def crawl_all_async():
    """모든 소스 동시 크롤링"""
    tasks = [
        crawl_async('domestic'),
        crawl_async('international')
    ]

    results = await asyncio.gather(*tasks)
    return results

# 실행
results = asyncio.run(crawl_all_async())
```

---

## 🧪 테스트 가이드

### 단위 테스트

**test_unit.py**:
```python
import unittest
from notam_crawler_api import NOTAMCrawlerAPI
from notam_change_detector import NOTAMChangeDetector

class TestNOTAMCrawler(unittest.TestCase):

    def setUp(self):
        self.crawler = NOTAMCrawlerAPI()

    def test_get_search_payload(self):
        """페이로드 생성 테스트"""
        payload = self.crawler.get_search_payload('domestic', 24)

        self.assertEqual(payload['sch_inorout'], 'N')
        self.assertIn('RKSI', payload['sch_airport'])
        self.assertIn('A', payload['sch_series'])

    def test_parse_json_response(self):
        """JSON 파싱 테스트"""
        json_data = '''
        {
            "DATA": [
                {
                    "NOTAM_NO": "A1234/25",
                    "LOCATION": "RKSI",
                    "AIS_TYPE": "A"
                }
            ],
            "Total": 1
        }
        '''

        notams = self.crawler._parse_json_response(json_data)

        self.assertEqual(len(notams), 1)
        self.assertEqual(notams[0]['notam_no'], 'A1234/25')

    def tearDown(self):
        self.crawler.close()

class TestChangeDetector(unittest.TestCase):

    def setUp(self):
        self.detector = NOTAMChangeDetector(':memory:')  # 메모리 DB

    def test_compare_notams(self):
        """NOTAM 비교 테스트"""
        previous = {'qcode': 'QWLC', 'status': 'ACTIVE'}
        current = {'qcode': 'QWLC', 'status': 'CANCELLED'}

        changes = self.detector.compare_notams(previous, current)

        self.assertIn('status', changes)
        self.assertEqual(changes['status']['previous'], 'ACTIVE')
        self.assertEqual(changes['status']['current'], 'CANCELLED')

    def test_detect_new_notam(self):
        """신규 NOTAM 감지 테스트"""
        # 빈 DB에 NOTAM 추가
        current_notams = [
            {'notam_no': 'A1234/25', 'location': 'RKSI'}
        ]

        changes = self.detector.detect_changes(current_notams, 'domestic')

        self.assertEqual(len(changes['new']), 1)
        self.assertEqual(changes['new'][0]['notam_no'], 'A1234/25')

    def tearDown(self):
        self.detector.close()

if __name__ == '__main__':
    unittest.main()
```

실행:
```bash
python -m unittest test_unit.py
```

### 통합 테스트

**test_integration.py**:
```python
import unittest
from notam_monitor import NOTAMMonitor
import sqlite3
import os

class TestIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """테스트 DB 생성"""
        cls.test_db = 'test_notam.db'
        cls.monitor = NOTAMMonitor(db_name=cls.test_db)

    def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        # 1. 크롤링
        result = self.monitor.monitor_single(
            'domestic',
            hours_back=24,
            enable_change_detection=True
        )

        self.assertEqual(result['status'], 'SUCCESS')
        self.assertGreater(result['crawl_result']['records_found'], 0)

        # 2. DB 확인
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notam_records")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertGreater(count, 0)

    @classmethod
    def tearDownClass(cls):
        """테스트 DB 삭제"""
        cls.monitor.close()
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)

if __name__ == '__main__':
    unittest.main()
```

### 부하 테스트

**locustfile.py** (Locust 사용):
```python
from locust import HttpUser, task, between

class NOTAMAPIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_notams(self):
        self.client.get("/api/notams?data_source=domestic&limit=100")

    @task(2)
    def get_changes(self):
        self.client.get("/api/changes?data_source=domestic&hours=24")

    @task(1)
    def get_stats(self):
        self.client.get("/api/stats?hours=24")

    @task(1)
    def health_check(self):
        self.client.get("/api/health")
```

실행:
```bash
pip install locust
locust -f locustfile.py --host=http://localhost:5000
```

웹 UI: http://localhost:8089

---

## 🐛 문제 해결

### 1. Chrome 드라이버 버전 불일치

**증상**:
```
selenium.common.exceptions.SessionNotCreatedException:
Message: session not created: This version of ChromeDriver only supports Chrome version XX
```

**해결**:
```bash
# Chrome 버전 확인
google-chrome --version

# 해당 버전 드라이버 다운로드
https://chromedriver.chromium.org/downloads

# 또는 webdriver-manager 사용
pip install webdriver-manager

# 코드 수정
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

driver = webdriver.Chrome(ChromeDriverManager().install())
```

### 2. Windows 인코딩 오류

**증상**:
```
UnicodeEncodeError: 'charmap' codec can't encode character
```

**해결**:
이미 코드에 포함되어 있음. 수동 설정:
```python
import sys
import os

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
```

### 3. SQLite 잠금 오류

**증상**:
```
sqlite3.OperationalError: database is locked
```

**해결**:
```python
import sqlite3

# timeout 설정
conn = sqlite3.connect('notam_realtime.db', timeout=30)

# 또는 WAL 모드 사용
conn.execute('PRAGMA journal_mode=WAL')
```

### 4. PostgreSQL 연결 실패

**증상**:
```
psycopg2.OperationalError: could not connect to server
```

**해결**:
```bash
# 1. PostgreSQL 실행 확인
sudo systemctl status postgresql

# 2. 방화벽 확인
sudo ufw allow 5432/tcp

# 3. pg_hba.conf 수정
sudo nano /etc/postgresql/14/main/pg_hba.conf

# 다음 줄 추가
host    all    all    0.0.0.0/0    md5

# 4. postgresql.conf 수정
sudo nano /etc/postgresql/14/main/postgresql.conf

listen_addresses = '*'

# 5. 재시작
sudo systemctl restart postgresql
```

### 5. 메모리 부족

**증상**:
```
MemoryError: Unable to allocate memory
```

**해결**:
```python
# 배치 크기 줄이기
def save_to_database_batch(self, notam_list, batch_size=100):
    for i in range(0, len(notam_list), batch_size):
        batch = notam_list[i:i+batch_size]
        self.save_to_database(batch)

# 또는 제너레이터 사용
def process_notams_generator(notam_list):
    for notam in notam_list:
        yield process(notam)
```

---

## 📊 성능 및 최적화

### 현재 성능

| 지표 | API 크롤러 | Selenium | 하이브리드 |
|------|-----------|----------|-----------|
| 평균 실행 시간 | 0.2초 | 15초 | 0.25초* |
| 성공률 | 98% | 95% | 99.5% |
| CPU 사용량 | 낮음 | 높음 | 낮음 |
| 메모리 사용량 | ~50MB | ~500MB | ~100MB |

*API 성공 시 기준

### 최적화 권장사항

**1. 데이터베이스 인덱스**
```sql
-- 현재 사용 중인 쿼리 분석
EXPLAIN ANALYZE SELECT * FROM notam_records
WHERE data_source = 'domestic'
  AND location = 'RKSI'
  AND status = 'ACTIVE';

-- 복합 인덱스 추가 (순서 중요!)
CREATE INDEX idx_complex ON notam_records(data_source, location, status, issue_time DESC);
```

**2. 연결 풀링**
```python
from psycopg2 import pool

# 연결 풀 생성
connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host='localhost',
    database='notam_db',
    user='notam_user',
    password='password'
)

# 사용
conn = connection_pool.getconn()
# ... 쿼리 실행
connection_pool.putconn(conn)
```

**3. 캐싱 전략**
```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=128)
def get_active_notams_cached(data_source, location, timestamp_minute):
    """5분 캐싱"""
    return query_database(data_source, location)

# 사용 (매 분 캐시 무효화)
current_minute = datetime.now().strftime('%Y-%m-%d %H:%M')
notams = get_active_notams_cached('domestic', 'RKSI', current_minute)
```

**4. 비동기 처리**
```python
import concurrent.futures

def crawl_all_parallel():
    """병렬 크롤링"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_domestic = executor.submit(crawler.crawl_notam, 'domestic', 24)
        future_intl = executor.submit(crawler.crawl_notam, 'international', 24)

        domestic_result = future_domestic.result()
        intl_result = future_intl.result()

        return {
            'domestic': domestic_result,
            'international': intl_result
        }
```

---

## 📞 지원 및 문의

### 문서
- **프로젝트 README**: `README.md`
- **상세 문서**: `PROJECT_README.md` (이 파일)
- **DB 스키마**: `DATABASE_SCHEMA_README.md`
- **구현 요약**: `IMPLEMENTATION_SUMMARY.md`

### 이슈 트래킹
- 버그 리포트: GitHub Issues
- 기능 요청: GitHub Discussions
- 보안 취약점: 비공개로 제보

### 커뮤니티
- 사용자 포럼: (추후 개설)
- Slack 채널: (추후 개설)

---

## 📜 라이선스

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 🙏 감사의 말

- **대한민국 국토교통부 AIM 포털**: NOTAM 데이터 제공
- **Python 커뮤니티**: 훌륭한 라이브러리
- **오픈소스 기여자들**: Requests, Selenium, Flask, PostgreSQL 등
- **모든 사용자들**: 피드백 및 버그 리포트

---

## 📝 변경 이력

### v2.0.0 (2025-11-11)
- ✅ Phase 1 완료: 데이터 수집 시스템
  - API 직접 호출 크롤러
  - Selenium 크롤러 개선
  - 하이브리드 크롤러 구현
  - 엔터프라이즈급 데이터베이스
- ✅ Phase 2 완료: 변경 감지 시스템
  - 자동 변경 감지
  - 변경 이력 저장
  - 통합 모니터링 시스템
- 📝 문서화 완료

### v1.0.0 (2025-11-09)
- 초기 버전
- Selenium 기반 크롤러
- SQLite 데이터베이스

---

**마지막 업데이트**: 2025-11-11
**다음 마일스톤**: Phase 3 (REST API 서버) - 사용자 구현 예정
**문서 버전**: 2.0.0
