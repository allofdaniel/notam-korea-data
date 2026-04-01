-- PostgreSQL NOTAM 실시간 모니터링 스키마
-- 작성일: 2025-11-10
-- 설명: NOTAM 데이터를 실시간으로 수집하고 변경 이력을 추적하기 위한 스키마

-- 공항 마스터 테이블
CREATE TABLE IF NOT EXISTS airports (
    id SERIAL PRIMARY KEY,
    code VARCHAR(6) UNIQUE NOT NULL,
    name_kr VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    icao_code VARCHAR(4),
    iata_code VARCHAR(3),
    country VARCHAR(50),
    is_domestic BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NOTAM 마스터 데이터 테이블
CREATE TABLE IF NOT EXISTS notams (
    id SERIAL PRIMARY KEY,
    notam_no VARCHAR(20) NOT NULL,
    location VARCHAR(6) NOT NULL,
    notam_type VARCHAR(20) NOT NULL, -- TYPE (예: A, B, C, D, E, G, Z, SNOWTAM 등)
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, CANCELLED, REPLACED
    issue_time TIMESTAMP NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    qcode VARCHAR(50), -- Q-CODE (예: QWLC 등)
    raw_data JSONB, -- 원본 HTML/JSON 데이터
    parsed_data JSONB, -- 파싱된 구조화 데이터
    full_text TEXT, -- 전체 NOTAM 텍스트
    full_text_detail TEXT, -- 상세 설명
    airport_id INTEGER REFERENCES airports(id),
    crawl_batch_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 복합 유니크 제약 (NOTAM NO + Location)
    UNIQUE(notam_no, location)
);

-- NOTAM 변경 이력 테이블
CREATE TABLE IF NOT EXISTS notam_changes (
    id SERIAL PRIMARY KEY,
    notam_id INTEGER NOT NULL REFERENCES notams(id) ON DELETE CASCADE,
    notam_no VARCHAR(20) NOT NULL,
    location VARCHAR(6) NOT NULL,
    change_type VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE, STATUS_CHANGE
    previous_status VARCHAR(20),
    new_status VARCHAR(20),
    previous_data JSONB, -- 변경 전 데이터
    new_data JSONB, -- 변경 후 데이터
    change_details TEXT, -- 변경 내용 설명
    detected_by_crawler_batch_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 크롤링 배치 로그 테이블
CREATE TABLE IF NOT EXISTS crawl_batches (
    id SERIAL PRIMARY KEY,
    data_source VARCHAR(20) NOT NULL, -- domestic, international
    batch_timestamp TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'RUNNING', -- RUNNING, SUCCESS, FAILED, PARTIAL
    total_records INTEGER DEFAULT 0, -- 발견한 NOTAM 수
    new_records INTEGER DEFAULT 0, -- 신규 NOTAM
    updated_records INTEGER DEFAULT 0, -- 업데이트된 NOTAM
    skipped_records INTEGER DEFAULT 0, -- 중복/오류
    error_message TEXT,
    execution_time_ms INTEGER, -- 실행 시간 (밀리초)
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

-- 뷰: 최근 활성 NOTAM
CREATE OR REPLACE VIEW v_active_notams AS
SELECT
    n.id,
    n.notam_no,
    n.location,
    a.name_kr,
    n.notam_type,
    n.status,
    n.issue_time,
    n.start_time,
    n.end_time,
    n.qcode,
    n.full_text,
    n.created_at,
    n.updated_at
FROM notams n
LEFT JOIN airports a ON n.airport_id = a.id
WHERE n.status = 'ACTIVE'
ORDER BY n.issue_time DESC;

-- 뷰: NOTAM 변경 요약
CREATE OR REPLACE VIEW v_notam_changes_summary AS
SELECT
    nc.notam_no,
    nc.location,
    a.name_kr,
    nc.change_type,
    nc.previous_status,
    nc.new_status,
    nc.created_at,
    n.notam_type,
    n.full_text
FROM notam_changes nc
LEFT JOIN notams n ON nc.notam_id = n.id
LEFT JOIN airports a ON n.airport_id = a.id
ORDER BY nc.created_at DESC;

-- 뷰: 크롤링 배치 통계
CREATE OR REPLACE VIEW v_crawl_batch_stats AS
SELECT
    data_source,
    DATE(batch_timestamp) as crawl_date,
    COUNT(*) as total_batches,
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_batches,
    SUM(total_records) as total_records_found,
    SUM(new_records) as total_new_records,
    SUM(updated_records) as total_updated_records,
    AVG(execution_time_ms) as avg_execution_ms,
    MAX(execution_time_ms) as max_execution_ms
FROM crawl_batches
GROUP BY data_source, DATE(batch_timestamp)
ORDER BY DATE(batch_timestamp) DESC, data_source;

-- 함수: NOTAM 상태 변경 시 자동으로 변경 이력 기록
CREATE OR REPLACE FUNCTION log_notam_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO notam_changes (
            notam_id, notam_no, location, change_type,
            previous_status, new_status, new_data
        ) VALUES (
            NEW.id, NEW.notam_no, NEW.location, 'INSERT',
            NULL, NEW.status, to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status != NEW.status THEN
            INSERT INTO notam_changes (
                notam_id, notam_no, location, change_type,
                previous_status, new_status, previous_data, new_data
            ) VALUES (
                NEW.id, NEW.notam_no, NEW.location, 'STATUS_CHANGE',
                OLD.status, NEW.status, to_jsonb(OLD), to_jsonb(NEW)
            );
        ELSE
            INSERT INTO notam_changes (
                notam_id, notam_no, location, change_type,
                previous_data, new_data
            ) VALUES (
                NEW.id, NEW.notam_no, NEW.location, 'UPDATE',
                to_jsonb(OLD), to_jsonb(NEW)
            );
        END IF;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 트리거: NOTAM 변경 로깅
CREATE TRIGGER trig_log_notam_change
AFTER INSERT OR UPDATE ON notams
FOR EACH ROW EXECUTE FUNCTION log_notam_change();

-- 함수: updated_at 자동 업데이트
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거: 공항 updated_at 자동 업데이트
CREATE TRIGGER trig_update_airports_updated_at
BEFORE UPDATE ON airports
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 트리거: NOTAM updated_at 자동 업데이트
CREATE TRIGGER trig_update_notams_updated_at
BEFORE UPDATE ON notams
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
