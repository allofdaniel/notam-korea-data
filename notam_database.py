"""
NOTAM 데이터베이스 연결 레이어
작성일: 2025-11-10
설명: SQLite 기반 NOTAM 실시간 모니터링 DB 관리
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import uuid

# 로깅 설정
logger = logging.getLogger(__name__)


class NOTAMDatabase:
    """NOTAM 데이터베이스 관리 클래스"""

    def __init__(self, db_path='notam_realtime.db'):
        """
        데이터베이스 초기화

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.conn = None
        logger.info(f"NOTAMDatabase 초기화: {db_path}")

    def connect(self):
        """DB 연결"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"데이터베이스 연결 성공: {self.db_path}")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise

    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            logger.info("데이터베이스 연결 종료")

    def init_schema(self):
        """스키마 초기화"""
        try:
            schema_file = Path(__file__).parent / 'schema.sql'

            if not schema_file.exists():
                logger.error(f"스키마 파일을 찾을 수 없음: {schema_file}")
                return False

            with open(schema_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # 세미콜론 단위로 분할하여 실행
            statements = sql_content.split(';')
            cursor = self.conn.cursor()

            for statement in statements:
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)

            self.conn.commit()
            logger.info("스키마 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"스키마 초기화 실패: {e}")
            return False

    def insert_notam(self, notam_data: Dict) -> Optional[int]:
        """
        NOTAM 삽입 또는 업데이트

        Args:
            notam_data: NOTAM 데이터 딕셔너리
                - notam_no: NOTAM 번호 (필수)
                - location: 공항 코드 (필수)
                - series: SERIES 타입 (필수)
                - notam_type: TYPE (선택)
                - issue_time: 발행 시간 (필수)
                - start_time: 시작 시간 (선택)
                - end_time: 종료 시간 (선택)
                - qcode: Q-CODE (선택)
                - full_text: 전체 텍스트 (선택)
                - full_text_detail: 상세 텍스트 (선택)
                - raw_data: 원본 데이터 dict (선택)

        Returns:
            저장된 NOTAM의 ID
        """
        try:
            cursor = self.conn.cursor()

            # 기존 NOTAM 확인
            cursor.execute('''
                SELECT id, status FROM notams
                WHERE notam_no = ? AND location = ?
            ''', (notam_data['notam_no'], notam_data['location']))

            existing = cursor.fetchone()

            # series 추출 (NOTAM NO에서)
            series = notam_data.get('series', '')
            if not series and 'notam_no' in notam_data:
                # 예: A0001/25 -> A
                parts = notam_data['notam_no'].split('/')
                if parts and len(parts[0]) > 0:
                    series = parts[0][0]

            # raw_data JSON 변환
            raw_data = notam_data.get('raw_data')
            if raw_data and isinstance(raw_data, dict):
                raw_data = json.dumps(raw_data, ensure_ascii=False)

            if existing:
                # 업데이트
                notam_id = existing['id']
                cursor.execute('''
                    UPDATE notams SET
                        notam_type = ?,
                        issue_time = ?,
                        start_time = ?,
                        end_time = ?,
                        qcode = ?,
                        full_text = ?,
                        full_text_detail = ?,
                        raw_data = ?,
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    notam_data.get('notam_type'),
                    notam_data['issue_time'],
                    notam_data.get('start_time'),
                    notam_data.get('end_time'),
                    notam_data.get('qcode'),
                    notam_data.get('full_text'),
                    notam_data.get('full_text_detail'),
                    raw_data,
                    notam_id
                ))
                logger.debug(f"NOTAM 업데이트: {notam_data['notam_no']} (ID: {notam_id})")
            else:
                # 신규 삽입
                cursor.execute('''
                    INSERT INTO notams (
                        notam_no, location, series, status, notam_type,
                        issue_time, start_time, end_time, qcode,
                        full_text, full_text_detail, raw_data,
                        first_seen_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (
                    notam_data['notam_no'],
                    notam_data['location'],
                    series,
                    notam_data.get('status', 'ACTIVE'),
                    notam_data.get('notam_type'),
                    notam_data['issue_time'],
                    notam_data.get('start_time'),
                    notam_data.get('end_time'),
                    notam_data.get('qcode'),
                    notam_data.get('full_text'),
                    notam_data.get('full_text_detail'),
                    raw_data
                ))
                notam_id = cursor.lastrowid
                logger.debug(f"NOTAM 삽입: {notam_data['notam_no']} (ID: {notam_id})")

            self.conn.commit()
            return notam_id
        except Exception as e:
            logger.error(f"NOTAM 삽입 실패: {e}")
            self.conn.rollback()
            return None

    def get_last_snapshot(self) -> List[Dict]:
        """
        마지막 스냅샷 조회 (활성 상태의 모든 NOTAM)

        Returns:
            NOTAM 리스트
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM notams
                WHERE status = 'ACTIVE'
                ORDER BY last_seen_at DESC
            ''')

            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"스냅샷 조회 실패: {e}")
            return []

    def insert_change(self, change_data: Dict) -> Optional[int]:
        """
        변경 이력 삽입

        Args:
            change_data: 변경 데이터 딕셔너리
                - notam_id: NOTAM ID (필수)
                - change_type: 변경 유형 (NEW, MODIFIED, CANCELLED) (필수)
                - previous_data: 변경 전 데이터 dict (선택)
                - current_data: 변경 후 데이터 dict (선택)

        Returns:
            변경 이력 ID
        """
        try:
            cursor = self.conn.cursor()

            # 데이터 JSON 변환
            previous_data = change_data.get('previous_data')
            if previous_data and isinstance(previous_data, dict):
                previous_data = json.dumps(previous_data, ensure_ascii=False)

            current_data = change_data.get('current_data')
            if current_data and isinstance(current_data, dict):
                current_data = json.dumps(current_data, ensure_ascii=False)

            cursor.execute('''
                INSERT INTO notam_changes (
                    notam_id, change_type, previous_data, current_data, detected_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                change_data['notam_id'],
                change_data['change_type'],
                previous_data,
                current_data
            ))

            change_id = cursor.lastrowid
            self.conn.commit()
            logger.debug(f"변경 이력 삽입: {change_data['change_type']} (ID: {change_id})")
            return change_id
        except Exception as e:
            logger.error(f"변경 이력 삽입 실패: {e}")
            self.conn.rollback()
            return None

    def start_batch(self, batch_id: str, data_source: str) -> bool:
        """
        배치 시작

        Args:
            batch_id: 배치 ID (UUID 형식 권장)
            data_source: 데이터 소스 (domestic, international)

        Returns:
            성공 여부
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO crawl_batches (
                    id, data_source, start_time, status
                ) VALUES (?, ?, CURRENT_TIMESTAMP, 'RUNNING')
            ''', (batch_id, data_source))

            self.conn.commit()
            logger.info(f"배치 시작: {batch_id} ({data_source})")
            return True
        except Exception as e:
            logger.error(f"배치 시작 실패: {e}")
            self.conn.rollback()
            return False

    def complete_batch(self, batch_id: str, stats: Dict) -> bool:
        """
        배치 완료

        Args:
            batch_id: 배치 ID
            stats: 통계 데이터 딕셔너리
                - status: 상태 (SUCCESS, FAILED, PARTIAL)
                - notams_fetched: 가져온 NOTAM 수
                - notams_new: 신규 NOTAM 수
                - notams_modified: 수정된 NOTAM 수
                - errors_count: 에러 수
                - error_details: 에러 상세 (선택)

        Returns:
            성공 여부
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE crawl_batches SET
                    end_time = CURRENT_TIMESTAMP,
                    status = ?,
                    notams_fetched = ?,
                    notams_new = ?,
                    notams_modified = ?,
                    errors_count = ?,
                    error_details = ?
                WHERE id = ?
            ''', (
                stats.get('status', 'SUCCESS'),
                stats.get('notams_fetched', 0),
                stats.get('notams_new', 0),
                stats.get('notams_modified', 0),
                stats.get('errors_count', 0),
                stats.get('error_details'),
                batch_id
            ))

            self.conn.commit()
            logger.info(f"배치 완료: {batch_id} - {stats.get('status')}")
            return True
        except Exception as e:
            logger.error(f"배치 완료 실패: {e}")
            self.conn.rollback()
            return False

    def get_notam_by_no(self, notam_no: str, location: str) -> Optional[Dict]:
        """NOTAM 번호와 위치로 조회"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM notams
                WHERE notam_no = ? AND location = ?
            ''', (notam_no, location))

            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"NOTAM 조회 실패: {e}")
            return None

    def get_recent_changes(self, limit: int = 100) -> List[Dict]:
        """최근 변경 이력 조회"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT nc.*, n.notam_no, n.location
                FROM notam_changes nc
                JOIN notams n ON nc.notam_id = n.id
                ORDER BY nc.detected_at DESC
                LIMIT ?
            ''', (limit,))

            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"변경 이력 조회 실패: {e}")
            return []

    def get_batch_stats(self, limit: int = 10) -> List[Dict]:
        """배치 통계 조회"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM crawl_batches
                ORDER BY start_time DESC
                LIMIT ?
            ''', (limit,))

            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"배치 통계 조회 실패: {e}")
            return []

    def update_notam_status(self, notam_id: int, status: str) -> bool:
        """NOTAM 상태 업데이트"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE notams SET status = ?, last_seen_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, notam_id))

            self.conn.commit()
            logger.debug(f"NOTAM 상태 업데이트: ID {notam_id} -> {status}")
            return True
        except Exception as e:
            logger.error(f"NOTAM 상태 업데이트 실패: {e}")
            self.conn.rollback()
            return False


def test_database():
    """데이터베이스 테스트"""
    print("=" * 70)
    print("NOTAMDatabase 테스트")
    print("=" * 70)

    # 1. 데이터베이스 초기화
    print("\n[1] 데이터베이스 초기화")
    db = NOTAMDatabase('test_notam.db')
    db.connect()

    if db.init_schema():
        print("    [OK] 스키마 생성 완료")
    else:
        print("    [FAIL] 스키마 생성 실패")
        return

    # 2. 배치 시작
    print("\n[2] 배치 시작")
    batch_id = str(uuid.uuid4())
    if db.start_batch(batch_id, 'domestic'):
        print(f"    [OK] 배치 시작: {batch_id}")
    else:
        print("    [FAIL] 배치 시작 실패")

    # 3. 샘플 NOTAM 삽입
    print("\n[3] 샘플 NOTAM 삽입")
    sample_notam = {
        'notam_no': 'A0001/25',
        'location': 'RKSI',
        'series': 'A',
        'notam_type': 'A',
        'issue_time': datetime.now().isoformat(),
        'start_time': datetime.now().isoformat(),
        'end_time': datetime.now().isoformat(),
        'qcode': 'QWLC',
        'full_text': '테스트 NOTAM 내용',
        'raw_data': {'test': 'data', 'source': 'test'}
    }

    notam_id = db.insert_notam(sample_notam)
    if notam_id:
        print(f"    [OK] NOTAM 삽입 완료 (ID: {notam_id})")
    else:
        print("    [FAIL] NOTAM 삽입 실패")
        return

    # 4. 변경 이력 삽입
    print("\n[4] 변경 이력 삽입")
    change_data = {
        'notam_id': notam_id,
        'change_type': 'NEW',
        'current_data': sample_notam
    }

    change_id = db.insert_change(change_data)
    if change_id:
        print(f"    [OK] 변경 이력 삽입 완료 (ID: {change_id})")
    else:
        print("    [FAIL] 변경 이력 삽입 실패")

    # 5. 스냅샷 조회
    print("\n[5] 스냅샷 조회")
    snapshot = db.get_last_snapshot()
    print(f"    [OK] {len(snapshot)}개 활성 NOTAM 조회")
    if snapshot:
        print(f"        샘플: {snapshot[0]['notam_no']} - {snapshot[0]['location']}")

    # 6. 배치 완료
    print("\n[6] 배치 완료")
    stats = {
        'status': 'SUCCESS',
        'notams_fetched': 1,
        'notams_new': 1,
        'notams_modified': 0,
        'errors_count': 0
    }

    if db.complete_batch(batch_id, stats):
        print(f"    [OK] 배치 완료: {batch_id}")
    else:
        print("    [FAIL] 배치 완료 실패")

    # 7. 배치 통계 조회
    print("\n[7] 배치 통계 조회")
    batch_stats = db.get_batch_stats(limit=5)
    print(f"    [OK] {len(batch_stats)}개 배치 조회")
    if batch_stats:
        last_batch = batch_stats[0]
        print(f"        최근 배치: {last_batch['data_source']} - {last_batch['status']}")
        print(f"        NOTAM: {last_batch['notams_fetched']}개 (신규: {last_batch['notams_new']})")

    # 8. 데이터베이스 종료
    print("\n[8] 데이터베이스 종료")
    db.close()
    print("    [OK] 연결 종료")

    print("\n" + "=" * 70)
    print("테스트 완료")
    print("=" * 70)


if __name__ == '__main__':
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 테스트 실행
    test_database()
