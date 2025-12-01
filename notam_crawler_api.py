"""
대한민국 NOTAM API 크롤러 - 고성능 직접 API 호출 방식
작성일: 2025-11-10
성능 목표: 전체 크롤링 2-3초 이내
"""

import requests
import sqlite3
import time
import json
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode
import pytz

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


class NOTAMCrawlerAPI:
    """NOTAM API 직접 호출 크롤러 - 고성능 버전"""

    def __init__(self, db_name='notam_realtime.db'):
        """
        초기화

        Args:
            db_name (str): SQLite 데이터베이스 파일명
        """
        self.base_url = 'https://aim.koca.go.kr'
        self.search_endpoint = f'{self.base_url}/xNotam/searchAllNotam.do'
        self.db_name = db_name

        # 한국 공항 코드 + FIR 코드 (19개)
        # RKRR = 인천 FIR (E/D 시리즈 NOTAM 포함)
        self.airports = [
            'RKRR',  # FIR 코드 추가 (E/D 시리즈용)
            'RKSI', 'RKSS', 'RKPK', 'RKPC', 'RKPS', 'RKPU',
            'RKSM', 'RKTH', 'RKPD', 'RKTL', 'RKNW', 'RKJK',
            'RKJB', 'RKJY', 'RKJJ', 'RKTN', 'RKTU', 'RKNY'
        ]

        # NOTAM SERIES 타입
        self.series_types = ['A', 'C', 'D', 'E', 'G', 'Z', 'SNOWTAM']

        # HTTP 세션 (연결 재사용으로 성능 향상)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/xNotam/?language=ko_KR',
            'Connection': 'keep-alive'
        })

        # 데이터베이스 초기화
        self.setup_database()

        logger.info("[OK] NOTAM API 크롤러 초기화 완료")
        logger.info(f"[INFO] 공항 수: {len(self.airports)}개")
        logger.info(f"[INFO] SERIES 타입: {', '.join(self.series_types)}")

    def setup_database(self):
        """SQLite 데이터베이스 초기화 (기존 구조와 호환)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # NOTAM 데이터 테이블 (API 서버와 호환되는 스키마)
        # UNIQUE 제약 제거 - 모든 데이터 저장
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notam_number TEXT,
                a_location TEXT,
                b_start_time TEXT,
                c_end_time TEXT,
                d_schedule TEXT,
                e_text TEXT,
                f_lower_limit TEXT,
                g_upper_limit TEXT,
                collected_at TEXT,
                last_updated TEXT,
                q_code TEXT,
                series_type TEXT,
                full_text TEXT,
                status TEXT DEFAULT 'ACTIVE',
                crawl_timestamp TEXT
            )
        ''')

        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_a_location ON notams(a_location)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_b_start_time ON notams(b_start_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_c_end_time ON notams(c_end_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_q_code ON notams(q_code)')

        # 크롤링 로그 테이블
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
        conn.close()

    def get_utc_time(self) -> datetime:
        """현재 UTC 시간 반환"""
        return datetime.now(pytz.timezone('UTC'))

    def get_search_payload(self, data_source: str = 'domestic',
                          hours_back: int = 2,
                          start_date: datetime = None,
                          end_date: datetime = None) -> Dict[str, str]:
        """
        검색 API 요청 페이로드 생성

        Args:
            data_source (str): 'domestic' 또는 'international'
            hours_back (int): 과거 몇 시간부터 검색할지 (start_date가 없을 때)
            start_date (datetime): 명시적 시작 날짜 (선택)
            end_date (datetime): 명시적 종료 날짜 (선택)

        Returns:
            Dict[str, str]: API 요청 파라미터
        """
        # 명시적 날짜가 제공되면 사용, 아니면 hours_back 사용
        if start_date and end_date:
            start_time = start_date
            utc_now = end_date
        else:
            utc_now = self.get_utc_time()
            start_time = utc_now - timedelta(hours=hours_back)

        # 국내/국제 구분 ('D' 또는 'I')
        inorout = 'D' if data_source == 'domestic' else 'I'

        # 모든 공항을 ,로 구분하여 전달
        airport_str = ','.join(self.airports)

        # SERIES 타입 (SNOWTAM 제외하고 전달)
        series_str = ','.join([s for s in self.series_types if s != 'SNOWTAM'])

        payload = {
            'sch_inorout': inorout,
            'sch_airport': airport_str,
            'sch_from_date': start_time.strftime('%Y-%m-%d'),
            'sch_from_time': start_time.strftime('%H%M'),
            'sch_to_date': utc_now.strftime('%Y-%m-%d'),
            'sch_to_time': utc_now.strftime('%H%M'),
            'sch_series': series_str,
            'sch_snow_series': 'SNOWTAM',  # 설빙고시보 별도 필드
            'sch_notam_no': '',
            'sch_elevation_min': '',
            'sch_elevation_max': '',
            'sch_qcode': '',
            'sch_fir': '',
            'sch_full_text': '',
            'sch_select': ''
        }

        return payload

    def parse_ibsheet_response(self, response_text: str) -> List[Dict[str, str]]:
        """
        IBSheet XML/JSON 응답 파싱

        Args:
            response_text (str): API 응답 텍스트

        Returns:
            List[Dict[str, str]]: 파싱된 NOTAM 데이터 리스트
        """
        notam_list = []

        try:
            # IBSheet는 XML 기반 응답을 사용할 수 있음
            # 실제 응답 형식에 따라 파싱 로직 조정

            if '<TR>' in response_text or '<Data>' in response_text:
                # XML 형식 응답 파싱
                notam_list = self._parse_xml_response(response_text)
            elif response_text.strip().startswith('{') or response_text.strip().startswith('['):
                # JSON 형식 응답 파싱
                notam_list = self._parse_json_response(response_text)
            else:
                logger.warning(f"[WARN] 알 수 없는 응답 형식: {response_text[:200]}")

        except Exception as e:
            logger.error(f"[ERROR] 응답 파싱 실패: {e}")
            logger.debug(f"응답 내용: {response_text[:500]}")

        return notam_list

    def _parse_xml_response(self, xml_text: str) -> List[Dict[str, str]]:
        """
        XML 형식 IBSheet 응답 파싱

        Args:
            xml_text (str): XML 응답 텍스트

        Returns:
            List[Dict[str, str]]: NOTAM 데이터 리스트
        """
        notam_list = []

        try:
            import xml.etree.ElementTree as ET

            # XML 파싱
            root = ET.fromstring(xml_text)

            # <TR> 또는 <Row> 태그 찾기
            rows = root.findall('.//TR') or root.findall('.//Row')

            for row in rows:
                cells = row.findall('.//TD') or row.findall('.//Cell')

                if len(cells) < 10:
                    continue

                # IBSheet 컬럼 구조에 맞춰 데이터 추출
                # C2=TYPE, C3=ISSUE_TIME, C4=LOCATION, C5=NOTAM_NO, etc.
                notam = {
                    'notam_type': cells[1].text or '' if len(cells) > 1 else '',
                    'issue_time': cells[2].text or '' if len(cells) > 2 else '',
                    'location': cells[3].text or '' if len(cells) > 3 else '',
                    'notam_no': cells[4].text or '' if len(cells) > 4 else '',
                    'qcode': cells[5].text or '' if len(cells) > 5 else '',
                    'start_time': cells[6].text or '' if len(cells) > 6 else '',
                    'end_time': cells[7].text or '' if len(cells) > 7 else '',
                    'full_text': cells[8].text or '' if len(cells) > 8 else '',
                    'full_text_detail': cells[9].text or '' if len(cells) > 9 else ''
                }

                # NOTAM NO가 있는 경우만 추가
                if notam['notam_no'] and notam['notam_no'].strip():
                    notam_list.append(notam)

        except Exception as e:
            logger.error(f"[ERROR] XML 파싱 오류: {e}")

        return notam_list

    def _parse_json_response(self, json_text: str) -> List[Dict[str, str]]:
        """
        JSON 형식 응답 파싱

        Args:
            json_text (str): JSON 응답 텍스트

        Returns:
            List[Dict[str, str]]: NOTAM 데이터 리스트
        """
        notam_list = []

        try:
            data = json.loads(json_text)

            # JSON 구조에 따라 데이터 추출
            # API 응답 형식: {"DATA": [...], "Total": N}
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # 가능한 키: 'DATA', 'data', 'items', 'rows', 'records' 등
                items = (data.get('DATA') or data.get('data') or
                        data.get('items') or data.get('rows') or
                        data.get('records') or [])
            else:
                items = []

            for item in items:
                if isinstance(item, dict):
                    # API 응답 필드명 매핑
                    # AIS_TYPE: NOTAM 타입 (A, C, D, E, G, Z 등)
                    # ISSUE_TIME: 발행 시간
                    # LOCATION: 공항 코드
                    # NOTAM_NO: NOTAM 번호
                    # QCODE: Q 코드
                    # EFFECTIVESTART: 시작 시간
                    # EFFECTIVEEND: 종료 시간
                    # ECODE: E 코드 (간략 설명)
                    # FULL_TEXT: 전체 텍스트

                    notam = {
                        'notam_type': item.get('AIS_TYPE') or item.get('SERIES') or '',
                        'issue_time': item.get('ISSUE_TIME') or '',
                        'location': item.get('LOCATION') or '',
                        'notam_no': item.get('NOTAM_NO') or '',
                        'qcode': item.get('QCODE') or '',
                        'start_time': item.get('EFFECTIVESTART') or '',
                        'end_time': item.get('EFFECTIVEEND') or '',
                        'full_text': item.get('ECODE') or '',
                        'full_text_detail': item.get('FULL_TEXT') or ''
                    }

                    if notam['notam_no'] and notam['notam_no'].strip():
                        notam_list.append(notam)

        except Exception as e:
            logger.error(f"[ERROR] JSON 파싱 오류: {e}")

        return notam_list

    def fetch_notam_data(self, data_source: str = 'domestic',
                        hours_back: int = 2,
                        start_date: datetime = None,
                        end_date: datetime = None,
                        max_retries: int = 3) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """
        NOTAM 데이터 API 호출 및 가져오기

        Args:
            data_source (str): 'domestic' 또는 'international'
            hours_back (int): 과거 몇 시간부터 검색 (start_date가 없을 때)
            start_date (datetime): 명시적 시작 날짜 (선택)
            end_date (datetime): 명시적 종료 날짜 (선택)
            max_retries (int): 최대 재시도 횟수

        Returns:
            Tuple[List[Dict[str, str]], Optional[str]]: (NOTAM 리스트, 에러 메시지)
        """
        payload = self.get_search_payload(data_source, hours_back, start_date, end_date)

        logger.info(f"[API] {data_source.upper()} NOTAM 요청 중...")
        logger.debug(f"페이로드: {payload}")

        for attempt in range(1, max_retries + 1):
            try:
                # API 요청 (페이지네이션 처리)
                all_notams = []
                page = 1
                total_records = None

                while True:
                    # 페이지 파라미터 추가
                    payload['ibsheetPageNo'] = str(page)
                    payload['ibsheetRowPerPage'] = '100'

                    response = self.session.post(
                        self.search_endpoint,
                        data=payload,
                        timeout=30,
                        allow_redirects=True
                    )

                    response.raise_for_status()

                    logger.debug(f"[API] 페이지 {page} 응답 코드: {response.status_code}")

                    # JSON 응답 파싱
                    try:
                        json_data = response.json()
                        # 필드 매핑을 위해 _parse_json_response 호출
                        notams = self._parse_json_response(response.text)

                        # Total 값 확인 (첫 페이지에서만)
                        if page == 1 and 'Total' in json_data:
                            total_records = json_data['Total']
                            expected_pages = (total_records + 99) // 100
                            logger.info(f"[API] 전체 {total_records}개, 예상 페이지: {expected_pages}개")
                    except:
                        # JSON 파싱 실패 시 기존 방식 사용
                        notams = self.parse_ibsheet_response(response.text)

                    if not notams:
                        logger.info(f"[API] 페이지 {page}: 데이터 없음 - 수집 완료")
                        break

                    all_notams.extend(notams)
                    logger.info(f"[API] 페이지 {page}: {len(notams)}개 NOTAM 추출 (누적: {len(all_notams)}개)")

                    # Total 값과 비교하여 완료 확인
                    if total_records and len(all_notams) >= total_records:
                        logger.info(f"[API] 전체 데이터 수집 완료 ({len(all_notams)}/{total_records})")
                        break

                    # 100개 미만이면 마지막 페이지로 판단
                    if len(notams) < 100:
                        logger.info(f"[API] 마지막 페이지 도달 (페이지 {page})")
                        break

                    # 다음 페이지로
                    page += 1
                    time.sleep(0.5)  # API 부하 방지

                logger.info(f"[API] 총 {len(all_notams)}개 NOTAM 가져오기 성공")
                return all_notams, None

            except requests.exceptions.RequestException as e:
                error_msg = f"API 요청 실패 (시도 {attempt}/{max_retries}): {e}"
                logger.warning(f"[WARN] {error_msg}")

                if attempt < max_retries:
                    wait_time = 2 ** attempt  # 지수 백오프
                    logger.info(f"[INFO] {wait_time}초 후 재시도...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[ERROR] 최대 재시도 횟수 초과")
                    return [], error_msg

            except Exception as e:
                error_msg = f"예상치 못한 오류: {e}"
                logger.error(f"[ERROR] {error_msg}")
                return [], error_msg

        return [], "알 수 없는 오류"

    def save_to_database(self, notam_list: List[Dict[str, str]],
                        data_source: str,
                        crawl_timestamp: str) -> int:
        """
        NOTAM 데이터를 DB에 저장 (기존 구조와 호환)

        Args:
            notam_list (List[Dict[str, str]]): NOTAM 데이터 리스트
            data_source (str): 'domestic' 또는 'international'
            crawl_timestamp (str): 크롤링 타임스탬프

        Returns:
            int: 저장된 레코드 수
        """
        if not notam_list:
            return 0

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        saved_count = 0

        for notam in notam_list:
            try:
                # 필수 필드 체크
                notam_no = notam.get('notam_no')
                if not notam_no:
                    logger.warning(f"[WARN] NOTAM 번호 없음 - 건너뜀: {notam.get('location', 'Unknown')}")
                    continue

                # E-text 추출 (full_text에서 E) 섹션 추출)
                e_text = notam.get('full_text', '')
                if 'E)' in e_text:
                    e_text = e_text.split('E)')[1].split('\n')[0] if 'E)' in e_text else e_text

                # Q-Code에서 고도 정보 추출 (Q)RKRR/QXXX/I/BO/A/lower/upper/...)
                f_lower = ''
                g_upper = ''
                qcode_full = notam.get('full_text_detail', '')
                if 'Q)' in qcode_full:
                    q_line = [line for line in qcode_full.split('\n') if line.startswith('Q)')][0] if any(line.startswith('Q)') for line in qcode_full.split('\n')) else ''
                    parts = q_line.split('/')
                    if len(parts) >= 7:
                        f_lower = parts[5] if parts[5] != '000' else 'SFC'
                        g_upper = parts[6] if len(parts) > 6 else ''

                cursor.execute('''
                    INSERT INTO notams
                    (notam_number, a_location, b_start_time, c_end_time, d_schedule,
                     e_text, f_lower_limit, g_upper_limit, collected_at, last_updated,
                     q_code, series_type, full_text, status, crawl_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    notam_no, notam.get('location', ''), notam.get('start_time', ''),
                    notam.get('end_time', ''), '', e_text, f_lower, g_upper,
                    crawl_timestamp, crawl_timestamp, notam.get('qcode', ''),
                    notam.get('notam_type', ''), notam.get('full_text_detail', ''), 'ACTIVE', crawl_timestamp
                ))
                if cursor.rowcount > 0:
                    saved_count += 1
            except Exception as e:
                logger.error(f"[ERROR] DB 저장 오류: {e} - NOTAM: {notam.get('notam_no', 'Unknown')}")

        conn.commit()
        conn.close()

        return saved_count

    def log_crawl(self, crawl_timestamp: str, data_source: str,
                  status: str, records_found: int, records_saved: int,
                  error_message: Optional[str] = None,
                  execution_time: float = 0):
        """
        크롤링 로그 저장

        Args:
            crawl_timestamp (str): 크롤링 타임스탬프
            data_source (str): 'domestic' 또는 'international'
            status (str): 'SUCCESS' 또는 'FAILED'
            records_found (int): 발견된 레코드 수
            records_saved (int): 저장된 레코드 수
            error_message (Optional[str]): 에러 메시지
            execution_time (float): 실행 시간 (초)
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO crawl_logs
            (crawl_timestamp, data_source, status, records_found, records_saved,
             error_message, execution_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (crawl_timestamp, data_source, status, records_found,
              records_saved, error_message, execution_time))

        conn.commit()
        conn.close()

    def crawl_notam_api(self, data_source: str = 'domestic',
                       hours_back: int = 2,
                       start_date: datetime = None,
                       end_date: datetime = None) -> Dict:
        """
        NOTAM API 크롤링 실행 (메인 메서드)

        Args:
            data_source (str): 'domestic' 또는 'international'
            hours_back (int): 과거 몇 시간부터 검색 (start_date가 없을 때)
            start_date (datetime): 명시적 시작 날짜 (선택)
            end_date (datetime): 명시적 종료 날짜 (선택)

        Returns:
            Dict: 크롤링 결과
        """
        start_time = time.time()
        crawl_timestamp = datetime.now().isoformat()

        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"[START] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {data_source.upper()} NOTAM API 크롤링 시작")
            logger.info(f"{'='*70}")

            # API 호출
            notam_list, error = self.fetch_notam_data(data_source, hours_back, start_date, end_date)

            if error:
                execution_time = time.time() - start_time
                self.log_crawl(crawl_timestamp, data_source, 'FAILED',
                              0, 0, error, execution_time)

                return {
                    'status': 'FAILED',
                    'error': error,
                    'execution_time': execution_time
                }

            # DB 저장
            saved_count = self.save_to_database(notam_list, data_source, crawl_timestamp)
            logger.info(f"[INFO] DB 저장 완료: {saved_count}개")

            # 실행 시간
            execution_time = time.time() - start_time

            # 로그 저장
            self.log_crawl(crawl_timestamp, data_source, 'SUCCESS',
                          len(notam_list), saved_count, None, execution_time)

            # 샘플 데이터 출력
            if notam_list:
                logger.info("\n[INFO] 샘플 데이터 (최신 3개):")
                for i, notam in enumerate(notam_list[:3], 1):
                    logger.info(f"  {i}. {notam['notam_no']} - {notam['location']} ({notam['notam_type']})")
                    logger.info(f"     시작: {notam['start_time']}, 종료: {notam['end_time']}")

            logger.info(f"\n[OK] API 크롤링 완료 - 실행시간: {execution_time:.2f}초")

            return {
                'status': 'SUCCESS',
                'records_found': len(notam_list),
                'records_saved': saved_count,
                'execution_time': execution_time
            }

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"[ERROR] 크롤링 실패: {error_msg}")

            # 에러 로그 저장
            self.log_crawl(crawl_timestamp, data_source, 'FAILED',
                          0, 0, error_msg, execution_time)

            return {
                'status': 'FAILED',
                'error': error_msg,
                'execution_time': execution_time
            }

    def test_crawl(self) -> Dict:
        """
        테스트 크롤링 실행 (국내 + 국제)

        Returns:
            Dict: 크롤링 결과
        """
        logger.info("[TEST] 테스트 크롤링 시작...")

        # 국내 NOTAM
        domestic_result = self.crawl_notam_api('domestic')

        # 국제 NOTAM
        international_result = self.crawl_notam_api('international')

        return {
            'domestic': domestic_result,
            'international': international_result
        }

    def close(self):
        """세션 종료"""
        if self.session:
            self.session.close()


def main():
    """메인 실행 함수"""
    crawler = NOTAMCrawlerAPI()

    try:
        # 테스트 실행
        results = crawler.test_crawl()

        # 결과 출력
        print("\n" + "="*70)
        print("[SUMMARY] API 크롤링 결과 요약")
        print("="*70)

        total_time = 0
        total_records = 0

        for data_source, result in results.items():
            print(f"\n[TEST] {data_source.upper()} NOTAM:")
            if result['status'] == 'SUCCESS':
                print(f"  [OK] 성공 - {result['records_found']}개 발견, {result['records_saved']}개 저장")
                print(f"  [TIME] 실행시간: {result['execution_time']:.2f}초")
                total_time += result['execution_time']
                total_records += result['records_found']
            else:
                print(f"  [FAIL] 실패 - {result['error']}")
                print(f"  [TIME] 실행시간: {result['execution_time']:.2f}초")

        print(f"\n[TOTAL] 전체 실행시간: {total_time:.2f}초")
        print(f"[TOTAL] 전체 레코드: {total_records}개")

        # 성능 목표 달성 여부
        if total_time <= 3.0:
            print(f"\n[SUCCESS] 성능 목표 달성! (목표: 3초 이내, 실제: {total_time:.2f}초)")
        else:
            print(f"\n[INFO] 성능 개선 필요 (목표: 3초 이내, 실제: {total_time:.2f}초)")

    finally:
        crawler.close()


if __name__ == "__main__":
    main()
