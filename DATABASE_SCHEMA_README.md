# NOTAM 실시간 모니터링 데이터베이스 스키마

## 개요

NOTAM(Notices to Airmen) 실시간 모니터링 시스템을 위한 포괄적인 데이터베이스 스키마입니다.
PostgreSQL과 SQLite 모두 지원합니다.

## 데이터베이스 구조

### 1. 공항 마스터 테이블 (airports)

```sql
CREATE TABLE airports (
    id SERIAL PRIMARY KEY,
    code VARCHAR(6) UNIQUE NOT NULL,        -- 공항 코드 (RKSI, RKSS 등)
    name_kr VARCHAR(100) NOT NULL,          -- 한글 공항명
    name_en VARCHAR(100),                   -- 영문 공항명
    icao_code VARCHAR(4),                   -- ICAO 코드
    iata_code VARCHAR(3),                   -- IATA 코드
    country VARCHAR(50),                    -- 국가
    is_domestic BOOLEAN DEFAULT TRUE,       -- 국내 공항 여부
    is_active BOOLEAN DEFAULT TRUE,         -- 활성 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**초기 데이터:** 한국 18개 공항 포함 (RKSI, RKSS, RKPK 등)

### 2. NOTAM 마스터 테이블 (notams)

```sql
CREATE TABLE notams (
    id SERIAL PRIMARY KEY,
    notam_no VARCHAR(20) NOT NULL,          -- NOTAM 번호
    location VARCHAR(6) NOT NULL,           -- 공항 코드
    notam_type VARCHAR(20) NOT NULL,        -- NOTAM 타입 (A, C, D, E, G, Z 등)
    status VARCHAR(20) DEFAULT 'ACTIVE',    -- 상태 (ACTIVE, CANCELLED, REPLACED)
    issue_time TIMESTAMP NOT NULL,          -- 발행 시간
    start_time TIMESTAMP,                   -- 시작 시간
    end_time TIMESTAMP,                     -- 종료 시간
    qcode VARCHAR(50),                      -- Q-CODE (예: QWLC)
    raw_data JSONB,                         -- 원본 데이터 (JSON)
    parsed_data JSONB,                      -- 파싱된 구조화 데이터
    full_text TEXT,                         -- 전체 NOTAM 텍스트
    full_text_detail TEXT,                  -- 상세 설명
    airport_id INTEGER REFERENCES airports(id),
    crawl_batch_id INTEGER,                 -- 크롤링 배치 참조
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(notam_no, location)              -- 복합 유니크 키
);
```

**주요 인덱스:**
- `idx_notams_location`: 공항 코드 기반 빠른 검색
- `idx_notams_status`: 상태 기반 필터링
- `idx_notams_issue_time`: 시간순 정렬 (내림차순)
- `idx_notams_status_location`: 상태 + 공항 복합 검색
- `idx_notams_status_time`: 상태 + 시간 복합 검색

### 3. NOTAM 변경 이력 테이블 (notam_changes)

```sql
CREATE TABLE notam_changes (
    id SERIAL PRIMARY KEY,
    notam_id INTEGER NOT NULL REFERENCES notams(id) ON DELETE CASCADE,
    notam_no VARCHAR(20) NOT NULL,          -- NOTAM 번호
    location VARCHAR(6) NOT NULL,           -- 공항 코드
    change_type VARCHAR(20) NOT NULL,       -- 변경 유형
    previous_status VARCHAR(20),            -- 이전 상태
    new_status VARCHAR(20),                 -- 새로운 상태
    previous_data JSONB,                    -- 변경 전 데이터
    new_data JSONB,                         -- 변경 후 데이터
    change_details TEXT,                    -- 변경 내용 설명
    detected_by_crawler_batch_id INTEGER,   -- 감지한 크롤러 배치
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**변경 유형:**
- `INSERT`: 신규 NOTAM
- `UPDATE`: 데이터 업데이트
- `DELETE`: NOTAM 삭제
- `STATUS_CHANGE`: 상태 변경 (ACTIVE → CANCELLED 등)

**주요 인덱스:**
- `idx_notam_changes_notam_id`: NOTAM ID 기반 빠른 접근
- `idx_notam_changes_created_at`: 시간순 정렬
- `idx_notam_changes_batch_id`: 배치 기반 추적

### 4. 크롤링 배치 로그 테이블 (crawl_batches)

```sql
CREATE TABLE crawl_batches (
    id SERIAL PRIMARY KEY,
    data_source VARCHAR(20) NOT NULL,       -- domestic, international
    batch_timestamp TIMESTAMP NOT NULL,     -- 크롤링 시작 시간
    status VARCHAR(20) DEFAULT 'RUNNING',   -- RUNNING, SUCCESS, FAILED, PARTIAL
    total_records INTEGER DEFAULT 0,        -- 발견한 NOTAM 수
    new_records INTEGER DEFAULT 0,          -- 신규 NOTAM
    updated_records INTEGER DEFAULT 0,      -- 업데이트된 NOTAM
    skipped_records INTEGER DEFAULT 0,      -- 중복/오류
    error_message TEXT,                     -- 에러 메시지
    execution_time_ms INTEGER,              -- 실행 시간 (밀리초)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP                  -- 완료 시간
);
```

**주요 인덱스:**
- `idx_crawl_batches_data_source`: 데이터 소스 기반 검색
- `idx_crawl_batches_status`: 상태 기반 검색
- `idx_crawl_batches_timestamp`: 시간순 정렬

## 뷰 (Views)

### v_active_notams
최근 활성 NOTAM을 공항명과 함께 조회합니다.

```sql
SELECT * FROM v_active_notams
WHERE status = 'ACTIVE'
ORDER BY issue_time DESC;
```

### v_notam_changes_summary
NOTAM 변경 이력을 요약하여 조회합니다.

```sql
SELECT * FROM v_notam_changes_summary
ORDER BY created_at DESC;
```

### v_crawl_batch_stats
크롤링 배치 통계를 조회합니다.

```sql
SELECT * FROM v_crawl_batch_stats
WHERE crawl_date >= CURRENT_DATE - INTERVAL 7 DAY;
```

## 자동 트리거 및 함수

### 1. NOTAM 변경 로깅 (log_notam_change)
- NOTAM 테이블에 INSERT/UPDATE 발생 시 자동으로 변경 이력 기록
- 상태 변경 시 별도로 추적

### 2. updated_at 자동 업데이트 (update_updated_at)
- airports, notams 테이블의 UPDATE 시 updated_at 자동 갱신

## 파일 구조

```
C:\Users\allof\Desktop\code\
├── database/
│   ├── schema.sql              # PostgreSQL 스키마 (219줄)
│   ├── schema_sqlite.sql       # SQLite 스키마 (104줄)
│   └── seed_airports.sql       # 공항 초기 데이터 (45줄)
├── database.py                 # DB 관리 클래스 (750줄)
└── DATABASE_SCHEMA_README.md   # 이 파일
```

## database.py 모듈 사용법

### 1. DatabaseManager 클래스

```python
from database import DatabaseManager

# SQLite 초기화 (기본값)
db = DatabaseManager(db_type='sqlite')

# PostgreSQL 초기화
db = DatabaseManager(
    db_type='postgresql',
    connection_string='postgresql://user:password@localhost/notam_db'
)

# 환경변수로 자동 선택
db = DatabaseManager(db_type='auto')  # NOTAM_DB_TYPE 환경변수 확인
```

### 2. 테이블 생성

```python
# 스키마 파일에서 테이블 생성
db.create_tables()

# 공항 초기 데이터 로드
db.seed_airports()
```

### 3. NOTAM 저장

```python
notam_data = {
    'notam_no': 'A0001/25',
    'location': 'RKSI',
    'notam_type': 'A',
    'status': 'ACTIVE',
    'issue_time': '2025-11-10T15:30:00',
    'start_time': '2025-11-10T16:00:00',
    'end_time': '2025-11-10T18:00:00',
    'qcode': 'QWLC',
    'full_text': 'NOTAM text content',
    'parsed_data': {'key': 'value'}
}

notam_id = db.save_notam(notam_data, crawl_batch_id=1)
```

### 4. NOTAM 조회

```python
# 특정 NOTAM 조회
notam = db.get_notam('A0001/25', 'RKSI')

# 활성 NOTAM 목록 (모든 공항)
active_notams = db.get_active_notams(limit=100)

# 특정 공항의 활성 NOTAM
rksi_notams = db.get_active_notams(location='RKSI', limit=50)
```

### 5. 변경 이력 저장

```python
change_id = db.save_notam_change(
    notam_id=1,
    notam_no='A0001/25',
    location='RKSI',
    change_type='STATUS_CHANGE',
    previous_status='ACTIVE',
    new_status='CANCELLED',
    change_details='NOTAM 취소됨',
    crawler_batch_id=2
)
```

### 6. 크롤링 배치 관리

```python
# 배치 생성 (크롤링 시작)
batch_id = db.create_crawl_batch('domestic')

# ... 크롤링 작업 수행 ...

# 배치 업데이트 (크롤링 완료)
db.update_crawl_batch(
    batch_id=batch_id,
    status='SUCCESS',
    total_records=150,
    new_records=10,
    updated_records=5,
    skipped_records=0,
    execution_time_ms=45230
)
```

### 7. 통계 조회

```python
# 최근 7일 크롤링 통계
stats = db.get_crawl_stats(data_source='domestic', days=7)

# 모든 데이터 소스의 통계
all_stats = db.get_crawl_stats(days=7)
```

## 환경변수 설정

### PostgreSQL 사용 시

```bash
export NOTAM_DB_TYPE=postgresql
export NOTAM_DATABASE_URL=postgresql://user:password@localhost:5432/notam_db
```

### SQLite 사용 시

```bash
export NOTAM_DB_TYPE=sqlite
export NOTAM_SQLITE_PATH=/path/to/notam_realtime.db
```

## 주요 특징

### 1. 복합 유니크 키
- `NOTAM NO + Location` 조합으로 중복 저장 방지
- 같은 NOTAM이 여러 공항에 영향을 주는 경우 구분

### 2. 완벽한 감사 추적
- 모든 변경 사항이 `notam_changes` 테이블에 자동 기록
- 상태 변경, 데이터 업데이트, 신규/삭제 등 추적 가능

### 3. JSON 필드 지원
- `raw_data`: 원본 HTML 또는 JSON 저장
- `parsed_data`: 구조화된 데이터 저장
- PostgreSQL의 JSONB: 인덱싱 및 쿼리 최적화 지원
- SQLite의 TEXT: 표준 JSON 형식으로 저장

### 4. 성능 최적화
- 총 17개의 전략적 인덱스
- 공항, 상태, 시간별 빠른 검색
- 복합 조건 검색 최적화

### 5. 자동 타임스탐프
- `created_at`: 레코드 생성 시간 자동 기록
- `updated_at`: 레코드 수정 시간 자동 갱신

## 호환성

### PostgreSQL (권장 - 프로덕션용)
- 버전: 12.0 이상
- 장점: JSONB 인덱싱, 트리거, 뷰, 함수 완벽 지원

### SQLite (개발/테스트용)
- 버전: 3.8.0 이상
- 장점: 설치 불필요, 단일 파일 데이터베이스
- 제한: 일부 고급 기능 미지원 (JSONB 인덱싱 등)

## 예제 쿼리

### 1. 특정 공항의 활성 NOTAM 조회
```sql
SELECT notam_no, location, notam_type, issue_time, start_time, end_time
FROM notams
WHERE status = 'ACTIVE' AND location = 'RKSI'
ORDER BY issue_time DESC;
```

### 2. 최근 1시간 내 변경된 NOTAM
```sql
SELECT nc.*, n.notam_type, a.name_kr
FROM notam_changes nc
LEFT JOIN notams n ON nc.notam_id = n.id
LEFT JOIN airports a ON n.airport_id = a.id
WHERE nc.created_at >= NOW() - INTERVAL 1 HOUR
ORDER BY nc.created_at DESC;
```

### 3. 크롤링 배치 성공률
```sql
SELECT
    data_source,
    COUNT(*) as total_batches,
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM crawl_batches
WHERE created_at >= NOW() - INTERVAL 7 DAY
GROUP BY data_source;
```

### 4. 평균 NOTAM 생명 주기 (생성 ~ 종료)
```sql
SELECT
    location,
    COUNT(*) as notam_count,
    AVG(EXTRACT(EPOCH FROM (end_time - issue_time)) / 3600)::INT as avg_duration_hours
FROM notams
WHERE status = 'ACTIVE'
GROUP BY location
ORDER BY notam_count DESC;
```

## 마이그레이션 가이드

### 기존 SQLite 테이블에서 새 스키마로 마이그레이션

```python
from database import DatabaseManager

# 기존 데이터 읽기
old_conn = sqlite3.connect('notam_realtime.db')
old_cursor = old_conn.cursor()
old_cursor.execute('SELECT * FROM notam_records')
old_records = old_cursor.fetchall()

# 새 데이터베이스에 저장
db = DatabaseManager(db_type='sqlite')
db.create_tables()
db.seed_airports()

for record in old_records:
    notam_data = {
        'notam_no': record['notam_no'],
        'location': record['location'],
        'notam_type': record['notam_type'],
        'issue_time': record['issue_time'],
        # ... 기타 필드 ...
    }
    db.save_notam(notam_data)
```

## 트러블슈팅

### 문제: PostgreSQL 연결 실패
**해결책:**
```bash
# 연결 문자열 확인
echo $NOTAM_DATABASE_URL

# PostgreSQL 서버 실행 확인
psql -U user -d notam_db -c "SELECT 1"
```

### 문제: SQLite 데이터베이스 손상
**해결책:**
```bash
# 데이터베이스 무결성 검사
sqlite3 notam_realtime.db "PRAGMA integrity_check;"

# 데이터베이스 복구
sqlite3 notam_realtime.db ".dump" | sqlite3 notam_realtime_repaired.db
```

### 문제: 인덱스 성능 저하
**해결책:**
```sql
-- 인덱스 재구성 (PostgreSQL)
REINDEX;

-- 통계 업데이트 (PostgreSQL)
ANALYZE;

-- 데이터베이스 최적화 (SQLite)
VACUUM;
PRAGMA optimize;
```

## 관련 파일

- **schema.sql**: PostgreSQL 완전 스키마 (219줄)
- **schema_sqlite.sql**: SQLite 호환 스키마 (104줄)
- **seed_airports.sql**: 한국 공항 18개 초기 데이터 (45줄)
- **database.py**: Python DatabaseManager 클래스 (750줄)

## 라이선스 및 관련 정보

- 작성일: 2025-11-10
- 지원 버전: PostgreSQL 12+, SQLite 3.8+
- 요구사항: Python 3.7+, psycopg2 (PostgreSQL 사용 시)

