-- SQLite NOTAM 실시간 모니터링 스키마
-- 작성일: 2025-11-10
-- 설명: 로컬 테스트용 SQLite 버전 (PostgreSQL 스키마와 동일한 구조)

-- 공항 마스터 테이블
CREATE TABLE IF NOT EXISTS airports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(6) UNIQUE NOT NULL,
    name_kr VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    icao_code VARCHAR(4),
    iata_code VARCHAR(3),
    country VARCHAR(50),
    is_domestic BOOLEAN DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NOTAM 마스터 데이터 테이블
CREATE TABLE IF NOT EXISTS notams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notam_no VARCHAR(20) NOT NULL,
    location VARCHAR(6) NOT NULL,
    notam_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, CANCELLED, REPLACED
    issue_time TIMESTAMP NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    qcode VARCHAR(50),
    raw_data TEXT, -- JSON 문자열 저장
    parsed_data TEXT, -- JSON 문자열 저장
    full_text TEXT,
    full_text_detail TEXT,
    airport_id INTEGER REFERENCES airports(id),
    crawl_batch_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 복합 유니크 제약
    UNIQUE(notam_no, location)
);

-- NOTAM 변경 이력 테이블
CREATE TABLE IF NOT EXISTS notam_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notam_id INTEGER NOT NULL REFERENCES notams(id) ON DELETE CASCADE,
    notam_no VARCHAR(20) NOT NULL,
    location VARCHAR(6) NOT NULL,
    change_type VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE, STATUS_CHANGE
    previous_status VARCHAR(20),
    new_status VARCHAR(20),
    previous_data TEXT, -- JSON 문자열
    new_data TEXT, -- JSON 문자열
    change_details TEXT,
    detected_by_crawler_batch_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 크롤링 배치 로그 테이블
CREATE TABLE IF NOT EXISTS crawl_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_source VARCHAR(20) NOT NULL, -- domestic, international
    batch_timestamp TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'RUNNING', -- RUNNING, SUCCESS, FAILED, PARTIAL
    total_records INTEGER DEFAULT 0,
    new_records INTEGER DEFAULT 0,
    updated_records INTEGER DEFAULT 0,
    skipped_records INTEGER DEFAULT 0,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- NOTAM 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_notams_location ON notams(location);
CREATE INDEX IF NOT EXISTS idx_notams_status ON notams(status);
CREATE INDEX IF NOT EXISTS idx_notams_issue_time ON notams(issue_time DESC);
CREATE INDEX IF NOT EXISTS idx_notams_start_time ON notams(start_time);
CREATE INDEX IF NOT EXISTS idx_notams_end_time ON notams(end_time);
CREATE INDEX IF NOT EXISTS idx_notams_notam_no ON notams(notam_no);
CREATE INDEX IF NOT EXISTS idx_notams_airport_id ON notams(airport_id);
CREATE INDEX IF NOT EXISTS idx_notams_status_location ON notams(status, location);
CREATE INDEX IF NOT EXISTS idx_notams_status_time ON notams(status, issue_time DESC);
CREATE INDEX IF NOT EXISTS idx_notams_created_at ON notams(created_at DESC);

-- NOTAM 변경 이력 인덱스
CREATE INDEX IF NOT EXISTS idx_notam_changes_notam_id ON notam_changes(notam_id);
CREATE INDEX IF NOT EXISTS idx_notam_changes_location ON notam_changes(location);
CREATE INDEX IF NOT EXISTS idx_notam_changes_change_type ON notam_changes(change_type);
CREATE INDEX IF NOT EXISTS idx_notam_changes_created_at ON notam_changes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notam_changes_batch_id ON notam_changes(detected_by_crawler_batch_id);

-- 크롤링 배치 인덱스
CREATE INDEX IF NOT EXISTS idx_crawl_batches_data_source ON crawl_batches(data_source);
CREATE INDEX IF NOT EXISTS idx_crawl_batches_status ON crawl_batches(status);
CREATE INDEX IF NOT EXISTS idx_crawl_batches_timestamp ON crawl_batches(batch_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_batches_created_at ON crawl_batches(created_at DESC);

-- 공항 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_airports_code ON airports(code);
CREATE INDEX IF NOT EXISTS idx_airports_is_active ON airports(is_active);
CREATE INDEX IF NOT EXISTS idx_airports_is_domestic ON airports(is_domestic);
