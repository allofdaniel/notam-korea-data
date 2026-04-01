"""
NOTAM 변경 감지 시스템
작성일: 2025-11-11
기능:
  - 신규 NOTAM 감지
  - 기존 NOTAM 업데이트 감지
  - NOTAM 상태 변경 감지 (ACTIVE -> CANCELLED 등)
  - 삭제/만료 NOTAM 감지
"""

import sqlite3
import json
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
from difflib import unified_diff

# Windows 한국어 환경 인코딩 설정
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'detach'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    except:
        pass  # 이미 설정되어 있음

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NOTAMChangeDetector:
    """NOTAM 변경 감지 시스템"""

    def __init__(self, db_name='notam_realtime.db'):
        """
        초기화

        Args:
            db_name (str): SQLite 데이터베이스 파일명
        """
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row  # 딕셔너리 스타일 접근

        logger.info("[OK] NOTAM 변경 감지 시스템 초기화 완료")

    def get_previous_notams(self, data_source: Optional[str] = None) -> Dict[str, Dict]:
        """
        이전 크롤링에서 가져온 NOTAM 데이터 조회

        Args:
            data_source (str, optional): 'domestic' 또는 'international'

        Returns:
            Dict[str, Dict]: {notam_no: notam_data} 형식의 딕셔너리
        """
        cursor = self.conn.cursor()

        if data_source:
            query = """
                SELECT * FROM notam_records
                WHERE data_source = ?
            """
            cursor.execute(query, (data_source,))
        else:
            query = "SELECT * FROM notam_records"
            cursor.execute(query)

        notams = {}
        for row in cursor.fetchall():
            notam_no = row['notam_no']
            notams[notam_no] = dict(row)

        logger.debug(f"[INFO] 이전 NOTAM 데이터: {len(notams)}개")
        return notams

    def detect_changes(self, current_notams: List[Dict],
                      data_source: str = 'domestic') -> Dict:
        """
        NOTAM 변경사항 감지

        Args:
            current_notams (List[Dict]): 현재 크롤링한 NOTAM 리스트
            data_source (str): 'domestic' 또는 'international'

        Returns:
            Dict: 변경사항 정보
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"[START] {data_source.upper()} NOTAM 변경 감지")
        logger.info(f"{'='*70}\n")

        # 이전 데이터 가져오기
        previous_notams = self.get_previous_notams(data_source)

        # 현재 NOTAM을 딕셔너리로 변환
        current_notams_dict = {n['notam_no']: n for n in current_notams}

        # 변경사항 추적
        changes = {
            'new': [],        # 신규 NOTAM
            'updated': [],    # 업데이트된 NOTAM
            'deleted': [],    # 삭제/만료된 NOTAM
            'unchanged': 0    # 변경 없음
        }

        # 1. 신규 및 업데이트 감지
        for notam_no, current_notam in current_notams_dict.items():
            if notam_no not in previous_notams:
                # 신규 NOTAM
                changes['new'].append(current_notam)
                logger.info(f"[NEW] 신규 NOTAM: {notam_no} - {current_notam.get('location', 'N/A')}")
            else:
                # 기존 NOTAM - 변경 여부 확인
                previous_notam = previous_notams[notam_no]
                change_details = self.compare_notams(previous_notam, current_notam)

                if change_details:
                    changes['updated'].append({
                        'notam_no': notam_no,
                        'previous': previous_notam,
                        'current': current_notam,
                        'changes': change_details
                    })
                    logger.info(f"[UPDATE] 업데이트: {notam_no} - {', '.join(change_details.keys())}")
                else:
                    changes['unchanged'] += 1

        # 2. 삭제/만료 감지
        current_notam_nos = set(current_notams_dict.keys())
        previous_notam_nos = set(previous_notams.keys())
        deleted_notam_nos = previous_notam_nos - current_notam_nos

        for notam_no in deleted_notam_nos:
            changes['deleted'].append(previous_notams[notam_no])
            logger.info(f"[DELETED] 삭제/만료: {notam_no}")

        # 요약
        logger.info(f"\n{'='*70}")
        logger.info(f"[SUMMARY] 변경 감지 결과")
        logger.info(f"{'='*70}")
        logger.info(f"신규: {len(changes['new'])}개")
        logger.info(f"업데이트: {len(changes['updated'])}개")
        logger.info(f"삭제/만료: {len(changes['deleted'])}개")
        logger.info(f"변경 없음: {changes['unchanged']}개")
        logger.info(f"{'='*70}\n")

        return changes

    def compare_notams(self, previous: Dict, current: Dict) -> Dict[str, Dict]:
        """
        두 NOTAM 데이터를 비교하여 변경사항 반환

        Args:
            previous (Dict): 이전 NOTAM 데이터
            current (Dict): 현재 NOTAM 데이터

        Returns:
            Dict[str, Dict]: 변경된 필드와 이전/현재 값
        """
        changes = {}

        # 비교할 필드
        fields_to_compare = [
            'issue_time', 'location', 'notam_type', 'qcode',
            'start_time', 'end_time', 'full_text', 'full_text_detail'
        ]

        for field in fields_to_compare:
            prev_value = previous.get(field, '')
            curr_value = current.get(field, '')

            # 값이 다른 경우
            if prev_value != curr_value:
                changes[field] = {
                    'previous': prev_value,
                    'current': curr_value
                }

        return changes

    def save_change_log(self, notam_no: str, location: str,
                       change_type: str, change_details: Dict,
                       data_source: str = 'domestic',
                       crawl_batch_id: Optional[int] = None) -> int:
        """
        변경 로그를 change_logs 테이블에 저장

        Args:
            notam_no (str): NOTAM 번호
            location (str): 위치
            change_type (str): 'NEW', 'UPDATE', 'DELETE'
            change_details (Dict): 변경 상세 정보
            data_source (str): 'domestic' 또는 'international'
            crawl_batch_id (int, optional): 크롤링 배치 ID

        Returns:
            int: 변경 로그 ID
        """
        cursor = self.conn.cursor()

        # change_logs 테이블이 없으면 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS change_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                notam_no TEXT,
                location TEXT,
                data_source TEXT,
                change_type TEXT,
                change_details TEXT,
                crawl_batch_id INTEGER
            )
        ''')

        # 변경 로그 저장
        timestamp = datetime.now().isoformat()
        change_details_json = json.dumps(change_details, ensure_ascii=False)

        cursor.execute('''
            INSERT INTO change_logs
            (timestamp, notam_no, location, data_source, change_type,
             change_details, crawl_batch_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, notam_no, location, data_source, change_type,
              change_details_json, crawl_batch_id))

        self.conn.commit()

        return cursor.lastrowid

    def process_changes(self, changes: Dict, data_source: str = 'domestic',
                       crawl_batch_id: Optional[int] = None) -> Dict:
        """
        감지된 변경사항 처리 (로그 저장)

        Args:
            changes (Dict): detect_changes()에서 반환된 변경사항
            data_source (str): 'domestic' 또는 'international'
            crawl_batch_id (int, optional): 크롤링 배치 ID

        Returns:
            Dict: 처리 결과
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"[START] 변경사항 로그 저장")
        logger.info(f"{'='*70}\n")

        saved_count = 0

        # 1. 신규 NOTAM 로그
        for notam in changes['new']:
            self.save_change_log(
                notam_no=notam['notam_no'],
                location=notam.get('location', 'UNKNOWN'),
                change_type='NEW',
                change_details={'full_data': notam},
                data_source=data_source,
                crawl_batch_id=crawl_batch_id
            )
            saved_count += 1

        # 2. 업데이트 NOTAM 로그
        for update in changes['updated']:
            self.save_change_log(
                notam_no=update['notam_no'],
                location=update['current'].get('location', 'UNKNOWN'),
                change_type='UPDATE',
                change_details=update['changes'],
                data_source=data_source,
                crawl_batch_id=crawl_batch_id
            )
            saved_count += 1

        # 3. 삭제/만료 NOTAM 로그
        for notam in changes['deleted']:
            self.save_change_log(
                notam_no=notam['notam_no'],
                location=notam.get('location', 'UNKNOWN'),
                change_type='DELETE',
                change_details={'full_data': notam},
                data_source=data_source,
                crawl_batch_id=crawl_batch_id
            )
            saved_count += 1

        logger.info(f"[OK] 변경 로그 {saved_count}개 저장 완료\n")

        return {
            'status': 'SUCCESS',
            'saved_count': saved_count
        }

    def get_change_history(self, notam_no: Optional[str] = None,
                          location: Optional[str] = None,
                          change_type: Optional[str] = None,
                          limit: int = 100) -> List[Dict]:
        """
        변경 이력 조회

        Args:
            notam_no (str, optional): NOTAM 번호로 필터
            location (str, optional): 위치로 필터
            change_type (str, optional): 변경 유형으로 필터
            limit (int): 최대 반환 개수

        Returns:
            List[Dict]: 변경 이력 리스트
        """
        cursor = self.conn.cursor()

        query = "SELECT * FROM change_logs WHERE 1=1"
        params = []

        if notam_no:
            query += " AND notam_no = ?"
            params.append(notam_no)

        if location:
            query += " AND location = ?"
            params.append(location)

        if change_type:
            query += " AND change_type = ?"
            params.append(change_type)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # JSON 파싱
            if result.get('change_details'):
                try:
                    result['change_details'] = json.loads(result['change_details'])
                except:
                    pass
            results.append(result)

        return results

    def get_change_stats(self, data_source: Optional[str] = None,
                        hours: int = 24) -> Dict:
        """
        변경 통계 조회

        Args:
            data_source (str, optional): 'domestic' 또는 'international'
            hours (int): 최근 몇 시간

        Returns:
            Dict: 통계 정보
        """
        cursor = self.conn.cursor()

        # change_logs 테이블 존재 여부 확인
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='change_logs'
        """)

        if not cursor.fetchone():
            # 테이블이 없으면 빈 통계 반환
            return {}

        # 시간 필터 생성
        from datetime import timedelta
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        try:
            if data_source:
                query = """
                    SELECT change_type, COUNT(*) as count
                    FROM change_logs
                    WHERE data_source = ? AND timestamp >= ?
                    GROUP BY change_type
                """
                cursor.execute(query, (data_source, cutoff_time))
            else:
                query = """
                    SELECT change_type, COUNT(*) as count
                    FROM change_logs
                    WHERE timestamp >= ?
                    GROUP BY change_type
                """
                cursor.execute(query, (cutoff_time,))

            stats = {}
            for row in cursor.fetchall():
                stats[row['change_type']] = row['count']

            return stats

        except Exception as e:
            logger.error(f"[ERROR] 통계 조회 오류: {e}")
            return {}

    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()


def main():
    """테스트용 메인 함수"""
    # 테스트용으로 현재 DB의 NOTAM을 가져와서 변경 감지 시뮬레이션
    detector = NOTAMChangeDetector()

    try:
        # 현재 DB의 NOTAM 가져오기 (테스트)
        conn = sqlite3.connect('notam_realtime.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM notam_records WHERE data_source = 'domestic' LIMIT 10")
        current_notams = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if current_notams:
            # 변경 감지
            changes = detector.detect_changes(current_notams, data_source='domestic')

            # 변경 로그 저장
            result = detector.process_changes(changes, data_source='domestic')

            print(f"\n✅ 변경 감지 테스트 완료: {result['saved_count']}개 로그 저장")

            # 통계 조회
            stats = detector.get_change_stats(data_source='domestic', hours=24)
            print(f"\n📊 최근 24시간 변경 통계:")
            for change_type, count in stats.items():
                print(f"  {change_type}: {count}개")
        else:
            print("⚠️  DB에 NOTAM 데이터가 없습니다. 먼저 크롤링을 실행하세요.")

    except Exception as e:
        logger.error(f"[ERROR] 테스트 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())

    finally:
        detector.close()


if __name__ == '__main__':
    main()
