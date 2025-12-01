-- NOTAM Korea 데이터베이스 인덱스 추가
-- 실행 방법: sqlite3 notam_database.db < add_db_indexes.sql

-- 1. notam_number 인덱스 (UNIQUE 제약조건으로 이미 존재할 수 있음)
CREATE INDEX IF NOT EXISTS idx_notam_number ON notams(notam_number);

-- 2. a_location 인덱스 (공항별 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_a_location ON notams(a_location);

-- 3. b_start_time 인덱스 (시간순 정렬 최적화)
CREATE INDEX IF NOT EXISTS idx_b_start_time ON notams(b_start_time);

-- 4. c_end_time 인덱스 (만료 NOTAM 조회)
CREATE INDEX IF NOT EXISTS idx_c_end_time ON notams(c_end_time);

-- 5. q_code 인덱스 (타입별 필터링)
CREATE INDEX IF NOT EXISTS idx_q_code ON notams(q_code);

-- 6. 복합 인덱스: 공항 + 시작시간 (공항별 최신 NOTAM 조회)
CREATE INDEX IF NOT EXISTS idx_location_start ON notams(a_location, b_start_time DESC);

-- 7. 복합 인덱스: Q-code + 시작시간 (타입별 최신 NOTAM)
CREATE INDEX IF NOT EXISTS idx_qcode_start ON notams(q_code, b_start_time DESC);

-- 인덱스 확인
SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='notams';

-- 데이터베이스 최적화
ANALYZE;
VACUUM;
