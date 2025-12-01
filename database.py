"""
NOTAM 실시간 모니터링 데이터베이스 관리 모듈
작성일: 2025-11-10
설명: PostgreSQL/SQLite 자동 선택, 스키마 관리, NOTAM 데이터 저장/조회
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import sys

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """데이터베이스 관리 클래스 (PostgreSQL/SQLite 지원)"""

    def __init__(self, db_type: str = 'auto', connection_string: str = None):
        """
        데이터베이스 관리자 초기화

        Args:
            db_type: 'postgresql', 'sqlite', 또는 'auto' (환경변수 확인)
            connection_string: 데이터베이스 연결 문자열
                - PostgreSQL: "postgresql://user:password@localhost/dbname"
                - SQLite: "/path/to/database.db"
        """
        self.db_type = self._determine_db_type(db_type)
        self.connection_string = connection_string or self._get_connection_string()
        self.conn = None
        self.cursor = None

        logger.info(f"DatabaseManager 초기화 - 유형: {self.db_type}")
        self._connect()

    def _determine_db_type(self, db_type: str) -> str:
        """데이터베이스 타입 결정"""
        if db_type != 'auto':
            return db_type

        # 환경변수에서 DB 타입 확인
        env_db_type = os.getenv('NOTAM_DB_TYPE', 'sqlite').lower()
        return env_db_type

    def _get_connection_string(self) -> str:
        """환경변수에서 연결 문자열 가져오기"""
        if self.db_type == 'postgresql':
            return os.getenv(
                'NOTAM_DATABASE_URL',
                'postgresql://notam_user:notam_password@localhost:5432/notam_db'
            )
        else:
            return os.getenv(
                'NOTAM_SQLITE_PATH',
                str(Path(__file__).parent / 'notam_realtime.db')
            )

    def _connect(self):
        """데이터베이스 연결"""
        try:
            if self.db_type == 'postgresql':
                import psycopg2
                from psycopg2.extras import RealDictCursor

                self.conn = psycopg2.connect(self.connection_string)
                self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
                logger.info(f"PostgreSQL 연결 성공: {self.connection_string.split('@')[1] if '@' in self.connection_string else 'localhost'}")
            else:
                # SQLite
                self.conn = sqlite3.connect(self.connection_string)
                self.conn.row_factory = sqlite3.Row
                self.cursor = self.conn.cursor()
                logger.info(f"SQLite 연결 성공: {self.connection_string}")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise

    def close(self):
        """데이터베이스 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("데이터베이스 연결 종료")

    def create_tables(self, schema_file: str = None):
        """스키마 파일에서 테이블 생성"""
        try:
            if schema_file is None:
                # 기본 스키마 파일 경로
                if self.db_type == 'postgresql':
                    schema_file = Path(__file__).parent / 'database' / 'schema.sql'
                else:
                    schema_file = Path(__file__).parent / 'database' / 'schema_sqlite.sql'

            if not Path(schema_file).exists():
                logger.warning(f"스키마 파일을 찾을 수 없음: {schema_file}")
                return False

            with open(schema_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # SQLite는 세미콜론 단위로 분할 필요
            if self.db_type == 'sqlite':
                statements = sql_content.split(';')
                for statement in statements:
                    statement = statement.strip()
                    if statement:
                        self.cursor.execute(statement)
                self.conn.commit()
            else:
                # PostgreSQL은 psycopg2가 자동으로 처리
                self.cursor.execute(sql_content)
                self.conn.commit()

            logger.info(f"테이블 생성 완료: {schema_file}")
            return True
        except Exception as e:
            logger.error(f"테이블 생성 실패: {e}")
            return False

    def seed_airports(self, seed_file: str = None) -> bool:
        """공항 초기 데이터 로드"""
        try:
            if seed_file is None:
                seed_file = Path(__file__).parent / 'database' / 'seed_airports.sql'

            if not Path(seed_file).exists():
                logger.warning(f"시드 파일을 찾을 수 없음: {seed_file}")
                return False

            with open(seed_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # 파일에서 INSERT 문 추출
            statements = [s.strip() for s in sql_content.split(';') if s.strip() and s.strip().startswith('INSERT')]

            if self.db_type == 'sqlite':
                for statement in statements:
                    self.cursor.execute(statement)
                self.conn.commit()
            else:
                for statement in statements:
                    self.cursor.execute(statement)
                self.conn.commit()

            logger.info(f"공항 데이터 로드 완료: {len(statements)}개")
            return True
        except Exception as e:
            logger.error(f"공항 데이터 로드 실패: {e}")
            return False

    def save_notam(self, notam_data: Dict[str, Any], crawl_batch_id: int = None) -> Optional[int]:
        """
        NOTAM 데이터 저장/업데이트

        Args:
            notam_data: NOTAM 데이터 딕셔너리
            crawl_batch_id: 크롤링 배치 ID

        Returns:
            저장된 NOTAM의 ID (성공 시) 또는 None
        """
        try:
            # 필수 필드 확인
            required_fields = ['notam_no', 'location', 'notam_type', 'issue_time']
            for field in required_fields:
                if field not in notam_data:
                    logger.warning(f"필수 필드 누락: {field}")
                    return None

            # 공항 ID 조회
            airport_id = None
            if notam_data.get('location'):
                airport_id = self.get_airport_id(notam_data['location'])

            # JSON 필드 처리
            raw_data = notam_data.get('raw_data')
            if raw_data and isinstance(raw_data, dict):
                raw_data = json.dumps(raw_data, ensure_ascii=False)

            parsed_data = notam_data.get('parsed_data')
            if parsed_data and isinstance(parsed_data, dict):
                parsed_data = json.dumps(parsed_data, ensure_ascii=False)

            # NOTAM 저장 SQL
            if self.db_type == 'postgresql':
                sql = """
                INSERT INTO notams (
                    notam_no, location, notam_type, status, issue_time,
                    start_time, end_time, qcode, raw_data, parsed_data,
                    full_text, full_text_detail, airport_id, crawl_batch_id,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                ON CONFLICT (notam_no, location) DO UPDATE SET
                    status = EXCLUDED.status,
                    issue_time = EXCLUDED.issue_time,
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time,
                    qcode = EXCLUDED.qcode,
                    raw_data = EXCLUDED.raw_data,
                    parsed_data = EXCLUDED.parsed_data,
                    full_text = EXCLUDED.full_text,
                    full_text_detail = EXCLUDED.full_text_detail,
                    crawl_batch_id = EXCLUDED.crawl_batch_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id;
                """
                values = (
                    notam_data['notam_no'], notam_data['location'],
                    notam_data['notam_type'], notam_data.get('status', 'ACTIVE'),
                    notam_data['issue_time'],
                    notam_data.get('start_time'),
                    notam_data.get('end_time'),
                    notam_data.get('qcode'),
                    raw_data, parsed_data,
                    notam_data.get('full_text'),
                    notam_data.get('full_text_detail'),
                    airport_id, crawl_batch_id
                )
                self.cursor.execute(sql, values)
                result = self.cursor.fetchone()
                notam_id = result[0] if result else None
            else:
                # SQLite
                sql = """
                INSERT OR REPLACE INTO notams (
                    notam_no, location, notam_type, status, issue_time,
                    start_time, end_time, qcode, raw_data, parsed_data,
                    full_text, full_text_detail, airport_id, crawl_batch_id,
                    created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                );
                """
                values = (
                    notam_data['notam_no'], notam_data['location'],
                    notam_data['notam_type'], notam_data.get('status', 'ACTIVE'),
                    notam_data['issue_time'],
                    notam_data.get('start_time'),
                    notam_data.get('end_time'),
                    notam_data.get('qcode'),
                    raw_data, parsed_data,
                    notam_data.get('full_text'),
                    notam_data.get('full_text_detail'),
                    airport_id, crawl_batch_id
                )
                self.cursor.execute(sql, values)
                notam_id = self.cursor.lastrowid

            self.conn.commit()
            logger.debug(f"NOTAM 저장 완료: {notam_data['notam_no']} (ID: {notam_id})")
            return notam_id
        except Exception as e:
            logger.error(f"NOTAM 저장 실패: {e}")
            self.conn.rollback()
            return None

    def save_notam_change(self, notam_id: int, notam_no: str, location: str,
                          change_type: str, previous_status: str = None,
                          new_status: str = None, previous_data: Dict = None,
                          new_data: Dict = None, change_details: str = None,
                          crawler_batch_id: int = None) -> Optional[int]:
        """
        NOTAM 변경 이력 저장

        Args:
            notam_id: NOTAM ID
            notam_no: NOTAM 번호
            location: 위치 (공항 코드)
            change_type: 변경 유형 (INSERT, UPDATE, DELETE, STATUS_CHANGE)
            previous_status: 이전 상태
            new_status: 새로운 상태
            previous_data: 변경 전 데이터
            new_data: 변경 후 데이터
            change_details: 변경 내용 설명
            crawler_batch_id: 크롤러 배치 ID

        Returns:
            저장된 변경 이력의 ID
        """
        try:
            # JSON 변환
            previous_data_json = json.dumps(previous_data, ensure_ascii=False) if previous_data else None
            new_data_json = json.dumps(new_data, ensure_ascii=False) if new_data else None

            if self.db_type == 'postgresql':
                sql = """
                INSERT INTO notam_changes (
                    notam_id, notam_no, location, change_type,
                    previous_status, new_status, previous_data, new_data,
                    change_details, detected_by_crawler_batch_id, created_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, CURRENT_TIMESTAMP
                ) RETURNING id;
                """
                values = (
                    notam_id, notam_no, location, change_type,
                    previous_status, new_status, previous_data_json, new_data_json,
                    change_details, crawler_batch_id
                )
                self.cursor.execute(sql, values)
                result = self.cursor.fetchone()
                change_id = result[0] if result else None
            else:
                # SQLite
                sql = """
                INSERT INTO notam_changes (
                    notam_id, notam_no, location, change_type,
                    previous_status, new_status, previous_data, new_data,
                    change_details, detected_by_crawler_batch_id, created_at
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, CURRENT_TIMESTAMP
                );
                """
                values = (
                    notam_id, notam_no, location, change_type,
                    previous_status, new_status, previous_data_json, new_data_json,
                    change_details, crawler_batch_id
                )
                self.cursor.execute(sql, values)
                change_id = self.cursor.lastrowid

            self.conn.commit()
            logger.debug(f"NOTAM 변경 이력 저장 완료: {notam_no} ({change_type})")
            return change_id
        except Exception as e:
            logger.error(f"NOTAM 변경 이력 저장 실패: {e}")
            self.conn.rollback()
            return None

    def create_crawl_batch(self, data_source: str) -> int:
        """
        크롤링 배치 생성

        Args:
            data_source: 데이터 소스 (domestic, international)

        Returns:
            생성된 배치 ID
        """
        try:
            if self.db_type == 'postgresql':
                sql = """
                INSERT INTO crawl_batches (
                    data_source, batch_timestamp, status, created_at
                ) VALUES (
                    %s, CURRENT_TIMESTAMP, 'RUNNING', CURRENT_TIMESTAMP
                ) RETURNING id;
                """
                self.cursor.execute(sql, (data_source,))
                result = self.cursor.fetchone()
                batch_id = result[0] if result else None
            else:
                # SQLite
                sql = """
                INSERT INTO crawl_batches (
                    data_source, batch_timestamp, status, created_at
                ) VALUES (
                    ?, CURRENT_TIMESTAMP, 'RUNNING', CURRENT_TIMESTAMP
                );
                """
                self.cursor.execute(sql, (data_source,))
                batch_id = self.cursor.lastrowid

            self.conn.commit()
            logger.info(f"크롤링 배치 생성: {batch_id} ({data_source})")
            return batch_id
        except Exception as e:
            logger.error(f"크롤링 배치 생성 실패: {e}")
            self.conn.rollback()
            return None

    def update_crawl_batch(self, batch_id: int, status: str, total_records: int = 0,
                          new_records: int = 0, updated_records: int = 0,
                          skipped_records: int = 0, error_message: str = None,
                          execution_time_ms: int = 0):
        """크롤링 배치 상태 업데이트"""
        try:
            if self.db_type == 'postgresql':
                sql = """
                UPDATE crawl_batches SET
                    status = %s,
                    total_records = %s,
                    new_records = %s,
                    updated_records = %s,
                    skipped_records = %s,
                    error_message = %s,
                    execution_time_ms = %s,
                    completed_at = CASE WHEN %s IN ('SUCCESS', 'FAILED', 'PARTIAL') THEN CURRENT_TIMESTAMP ELSE NULL END
                WHERE id = %s;
                """
                self.cursor.execute(sql, (
                    status, total_records, new_records, updated_records,
                    skipped_records, error_message, execution_time_ms,
                    status, batch_id
                ))
            else:
                # SQLite
                sql = """
                UPDATE crawl_batches SET
                    status = ?,
                    total_records = ?,
                    new_records = ?,
                    updated_records = ?,
                    skipped_records = ?,
                    error_message = ?,
                    execution_time_ms = ?,
                    completed_at = CASE WHEN ? IN ('SUCCESS', 'FAILED', 'PARTIAL') THEN CURRENT_TIMESTAMP ELSE NULL END
                WHERE id = ?;
                """
                self.cursor.execute(sql, (
                    status, total_records, new_records, updated_records,
                    skipped_records, error_message, execution_time_ms,
                    status, batch_id
                ))

            self.conn.commit()
            logger.info(f"크롤링 배치 업데이트: {batch_id} - {status}")
        except Exception as e:
            logger.error(f"크롤링 배치 업데이트 실패: {e}")
            self.conn.rollback()

    def get_notam(self, notam_no: str, location: str) -> Optional[Dict]:
        """NOTAM 조회"""
        try:
            if self.db_type == 'postgresql':
                sql = """
                SELECT * FROM notams
                WHERE notam_no = %s AND location = %s;
                """
                self.cursor.execute(sql, (notam_no, location))
            else:
                sql = """
                SELECT * FROM notams
                WHERE notam_no = ? AND location = ?;
                """
                self.cursor.execute(sql, (notam_no, location))

            result = self.cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"NOTAM 조회 실패: {e}")
            return None

    def get_active_notams(self, location: str = None, limit: int = 100) -> List[Dict]:
        """활성 NOTAM 목록 조회"""
        try:
            if location:
                if self.db_type == 'postgresql':
                    sql = """
                    SELECT n.*, a.name_kr
                    FROM notams n
                    LEFT JOIN airports a ON n.airport_id = a.id
                    WHERE n.status = 'ACTIVE' AND n.location = %s
                    ORDER BY n.issue_time DESC
                    LIMIT %s;
                    """
                    self.cursor.execute(sql, (location, limit))
                else:
                    sql = """
                    SELECT n.*, a.name_kr
                    FROM notams n
                    LEFT JOIN airports a ON n.airport_id = a.id
                    WHERE n.status = 'ACTIVE' AND n.location = ?
                    ORDER BY n.issue_time DESC
                    LIMIT ?;
                    """
                    self.cursor.execute(sql, (location, limit))
            else:
                if self.db_type == 'postgresql':
                    sql = """
                    SELECT n.*, a.name_kr
                    FROM notams n
                    LEFT JOIN airports a ON n.airport_id = a.id
                    WHERE n.status = 'ACTIVE'
                    ORDER BY n.issue_time DESC
                    LIMIT %s;
                    """
                    self.cursor.execute(sql, (limit,))
                else:
                    sql = """
                    SELECT n.*, a.name_kr
                    FROM notams n
                    LEFT JOIN airports a ON n.airport_id = a.id
                    WHERE n.status = 'ACTIVE'
                    ORDER BY n.issue_time DESC
                    LIMIT ?;
                    """
                    self.cursor.execute(sql, (limit,))

            results = self.cursor.fetchall()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"활성 NOTAM 조회 실패: {e}")
            return []

    def get_airport_id(self, code: str) -> Optional[int]:
        """공항 코드로 ID 조회"""
        try:
            if self.db_type == 'postgresql':
                sql = "SELECT id FROM airports WHERE code = %s;"
                self.cursor.execute(sql, (code,))
            else:
                sql = "SELECT id FROM airports WHERE code = ?;"
                self.cursor.execute(sql, (code,))

            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.debug(f"공항 ID 조회 실패: {code} - {e}")
            return None

    def get_notam_changes(self, notam_no: str = None, location: str = None,
                         limit: int = 100) -> List[Dict]:
        """NOTAM 변경 이력 조회"""
        try:
            if notam_no and location:
                if self.db_type == 'postgresql':
                    sql = """
                    SELECT * FROM notam_changes
                    WHERE notam_no = %s AND location = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """
                    self.cursor.execute(sql, (notam_no, location, limit))
                else:
                    sql = """
                    SELECT * FROM notam_changes
                    WHERE notam_no = ? AND location = ?
                    ORDER BY created_at DESC
                    LIMIT ?;
                    """
                    self.cursor.execute(sql, (notam_no, location, limit))
            else:
                if self.db_type == 'postgresql':
                    sql = """
                    SELECT * FROM notam_changes
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """
                    self.cursor.execute(sql, (limit,))
                else:
                    sql = """
                    SELECT * FROM notam_changes
                    ORDER BY created_at DESC
                    LIMIT ?;
                    """
                    self.cursor.execute(sql, (limit,))

            results = self.cursor.fetchall()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"변경 이력 조회 실패: {e}")
            return []

    def get_crawl_stats(self, data_source: str = None, days: int = 7) -> Dict:
        """크롤링 통계 조회"""
        try:
            if data_source:
                if self.db_type == 'postgresql':
                    sql = """
                    SELECT
                        data_source,
                        COUNT(*) as total_batches,
                        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_batches,
                        SUM(total_records) as total_records,
                        AVG(execution_time_ms) as avg_execution_ms
                    FROM crawl_batches
                    WHERE data_source = %s AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY data_source;
                    """
                    self.cursor.execute(sql, (data_source, days))
                else:
                    sql = """
                    SELECT
                        data_source,
                        COUNT(*) as total_batches,
                        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_batches,
                        SUM(total_records) as total_records,
                        AVG(execution_time_ms) as avg_execution_ms
                    FROM crawl_batches
                    WHERE data_source = ? AND created_at >= datetime('now', '-%s days')
                    GROUP BY data_source;
                    """
                    self.cursor.execute(sql, (data_source, days))
            else:
                if self.db_type == 'postgresql':
                    sql = """
                    SELECT
                        data_source,
                        COUNT(*) as total_batches,
                        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_batches,
                        SUM(total_records) as total_records,
                        AVG(execution_time_ms) as avg_execution_ms
                    FROM crawl_batches
                    WHERE created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY data_source;
                    """
                    self.cursor.execute(sql, (days,))
                else:
                    sql = """
                    SELECT
                        data_source,
                        COUNT(*) as total_batches,
                        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_batches,
                        SUM(total_records) as total_records,
                        AVG(execution_time_ms) as avg_execution_ms
                    FROM crawl_batches
                    WHERE created_at >= datetime('now', '-%s days')
                    GROUP BY data_source;
                    """
                    self.cursor.execute(sql, (days,))

            results = self.cursor.fetchall()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"크롤링 통계 조회 실패: {e}")
            return []


# 기존 호환성을 위한 함수들
def init_database(db_name: str = 'notam_realtime.db') -> sqlite3.Connection:
    """
    SQLite 데이터베이스 초기화 (레거시 지원)

    Args:
        db_name: 데이터베이스 파일명

    Returns:
        sqlite3 연결 객체
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # 기존 notam_records 테이블 호환성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notam_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_timestamp TEXT,
            data_source TEXT,
            notam_type TEXT,
            issue_time TEXT,
            location TEXT,
            notam_no TEXT UNIQUE,
            qcode TEXT,
            start_time TEXT,
            end_time TEXT,
            full_text TEXT,
            full_text_detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 기존 crawl_logs 테이블 호환성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crawl_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_timestamp TEXT,
            data_source TEXT,
            status TEXT,
            records_found INTEGER,
            records_saved INTEGER,
            error_message TEXT,
            execution_time REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    return conn


if __name__ == '__main__':
    # 테스트 코드
    print("NOTAM 데이터베이스 관리 모듈 테스트")
    print("=" * 60)

    # SQLite 데이터베이스 매니저 생성
    db = DatabaseManager(db_type='sqlite')

    # 테이블 생성
    print("\n[1] 테이블 생성 중...")
    if db.create_tables():
        print("    [OK] 테이블 생성 완료")
    else:
        print("    [FAIL] 테이블 생성 실패")

    # 공항 데이터 로드
    print("\n[2] 공항 데이터 로드 중...")
    if db.seed_airports():
        print("    [OK] 공항 데이터 로드 완료")
    else:
        print("    [FAIL] 공항 데이터 로드 실패")

    # 샘플 NOTAM 저장
    print("\n[3] 샘플 NOTAM 저장 중...")
    sample_notam = {
        'notam_no': 'A0001/25',
        'location': 'RKSI',
        'notam_type': 'A',
        'status': 'ACTIVE',
        'issue_time': datetime.now().isoformat(),
        'start_time': datetime.now().isoformat(),
        'end_time': datetime.now().isoformat(),
        'qcode': 'QWLC',
        'full_text': '테스트 NOTAM',
        'parsed_data': {'test': 'data'}
    }

    notam_id = db.save_notam(sample_notam)
    if notam_id:
        print(f"    [OK] NOTAM 저장 완료 (ID: {notam_id})")
    else:
        print("    [FAIL] NOTAM 저장 실패")

    # 활성 NOTAM 조회
    print("\n[4] 활성 NOTAM 조회 중...")
    active_notams = db.get_active_notams(limit=5)
    print(f"    [OK] {len(active_notams)}개의 활성 NOTAM 조회")
    for notam in active_notams[:3]:
        print(f"        - {notam.get('notam_no')}: {notam.get('location')}")

    # 데이터베이스 종료
    print("\n[5] 데이터베이스 종료")
    db.close()

    print("\n" + "=" * 60)
    print("테스트 완료")
