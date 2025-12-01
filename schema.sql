-- SQLite NOTAM 실시간 모니터링 스키마
-- 작성일: 2025-11-10
-- 설명: NOTAM 실시간 변경 추적 시스템

-- NOTAM 마스터 테이블
CREATE TABLE IF NOT EXISTS notams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notam_no VARCHAR(50) NOT NULL,
    location VARCHAR(4) NOT NULL,
    series CHAR(1) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    notam_type VARCHAR(10),

    -- 시간 정보
    issue_time TEXT NOT NULL,
    start_time TEXT,
    end_time TEXT,

    -- NOTAM 내용
    qcode VARCHAR(10),
    full_text TEXT,
    full_text_detail TEXT,

    -- 메타데이터
    raw_data TEXT,  -- JSON 형태로 저장
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(notam_no, location)
);

-- 변경 이력 테이블
CREATE TABLE IF NOT EXISTS notam_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notam_id INTEGER NOT NULL,
    change_type VARCHAR(20) NOT NULL,
    previous_data TEXT,
    current_data TEXT,
    detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (notam_id) REFERENCES notams(id)
);

-- 크롤링 배치 로그
CREATE TABLE IF NOT EXISTS crawl_batches (
    id TEXT PRIMARY KEY,
    data_source VARCHAR(20) NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status VARCHAR(20) NOT NULL,
    notams_fetched INTEGER DEFAULT 0,
    notams_new INTEGER DEFAULT 0,
    notams_modified INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_details TEXT
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_notams_location ON notams(location);
CREATE INDEX IF NOT EXISTS idx_notams_status ON notams(status);
CREATE INDEX IF NOT EXISTS idx_notams_last_seen ON notams(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_changes_type ON notam_changes(change_type);
CREATE INDEX IF NOT EXISTS idx_changes_detected ON notam_changes(detected_at);
