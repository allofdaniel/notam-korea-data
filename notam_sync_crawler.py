#!/usr/bin/env python3
"""
EC2 NOTAM 동기화 크롤러 - 기존 데이터 수집
국토교통부 AIM 포털에서 현재 활성화된 모든 NOTAM 수집
"""

import requests
import sqlite3
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List

class NOTAMSyncCrawler:
    """NOTAM 초기 동기화 크롤러"""

    def __init__(self, db_name='notam_realtime.db'):
        self.base_url = 'https://aim.koca.go.kr'
        self.search_endpoint = f'{self.base_url}/xNotam/searchAllNotam.do'
        self.db_name = db_name

        # 국내 공항 코드
        self.airports = [
            'RKSI', 'RKSS', 'RKPK', 'RKPC', 'RKTU', 'RKTN',
            'RKJY', 'RKJJ', 'RKJK', 'RKJB', 'RKNY', 'RKTH',
            'RKPU', 'RKPO', 'RKTI', 'RKJM', 'RKNW'
        ]

        # HTTP 세션
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/xNotam/?language=ko_KR'
        })

        # 데이터베이스 초기화
        self.setup_database()

    def setup_database(self):
        """데이터베이스 테이블 생성"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notam_number TEXT UNIQUE,
                a_location TEXT,
                b_start_time TEXT,
                c_end_time TEXT,
                d_schedule TEXT,
                e_text TEXT,
                f_lower_limit TEXT,
                g_upper_limit TEXT,
                q_code TEXT,
                series_type TEXT,
                collected_at TEXT,
                last_updated TEXT
            )
        ''')

        conn.commit()
        conn.close()
        print(f"✅ 데이터베이스 준비 완료: {self.db_name}")

    def fetch_notams(self, airport: str, days_back: int = 30) -> List[Dict]:
        """
        특정 공항의 NOTAM 수집 (최근 N일)

        Args:
            airport: ICAO 코드
            days_back: 과거 며칠까지 조회할지
        """
        notams = []

        # 날짜 범위 설정 (UTC)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        # 요청 데이터
        data = {
            'locIndicatorGroup': airport,
            'notamType': 'NOTAM',
            'notamSeries': '',  # 모든 시리즈
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'pageIndex': '1',
            'pageSize': '1000',
            'lang': 'ko'
        }

        try:
            response = self.session.post(
                self.search_endpoint,
                data=data,
                timeout=30
            )
            response.raise_for_status()

            # 응답 파싱
            response_text = response.text

            # JSON 파싱 시도
            if response_text.strip().startswith('{') or response_text.strip().startswith('['):
                notams = self._parse_json(response_text)
            # XML/IBSheet 파싱 시도
            elif '<' in response_text:
                notams = self._parse_xml(response_text)

        except Exception as e:
            print(f"  ❌ API 호출 실패: {e}")

        return notams

    def _parse_json(self, text: str) -> List[Dict]:
        """JSON 응답 파싱"""
        notams = []

        try:
            data = json.loads(text)

            # 데이터 추출
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = (data.get('DATA') or data.get('data') or
                        data.get('items') or data.get('records') or [])

            for item in items:
                if not isinstance(item, dict):
                    continue

                notam = {
                    'notam_number': item.get('NOTAM_NO') or item.get('notam_no') or '',
                    'a_location': item.get('LOCATION') or item.get('location') or '',
                    'b_start_time': item.get('EFFECTIVESTART') or item.get('start_time') or '',
                    'c_end_time': item.get('EFFECTIVEEND') or item.get('end_time') or '',
                    'd_schedule': '',
                    'e_text': item.get('FULL_TEXT') or item.get('ECODE') or item.get('full_text') or '',
                    'f_lower_limit': '',
                    'g_upper_limit': '',
                    'q_code': item.get('QCODE') or item.get('qcode') or '',
                    'series_type': item.get('AIS_TYPE') or item.get('SERIES') or '',
                }

                if notam['notam_number']:
                    notams.append(notam)

        except Exception as e:
            print(f"  JSON 파싱 오류: {e}")

        return notams

    def _parse_xml(self, text: str) -> List[Dict]:
        """XML/IBSheet 응답 파싱"""
        notams = []

        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(text)
            rows = root.findall('.//TR') or root.findall('.//Row')

            for row in rows:
                cells = row.findall('.//TD') or row.findall('.//Cell')

                if len(cells) < 8:
                    continue

                notam = {
                    'notam_number': (cells[4].text or '').strip() if len(cells) > 4 else '',
                    'a_location': (cells[3].text or '').strip() if len(cells) > 3 else '',
                    'b_start_time': (cells[6].text or '').strip() if len(cells) > 6 else '',
                    'c_end_time': (cells[7].text or '').strip() if len(cells) > 7 else '',
                    'd_schedule': '',
                    'e_text': (cells[8].text or '').strip() if len(cells) > 8 else '',
                    'f_lower_limit': '',
                    'g_upper_limit': '',
                    'q_code': (cells[5].text or '').strip() if len(cells) > 5 else '',
                    'series_type': (cells[1].text or '').strip() if len(cells) > 1 else '',
                }

                if notam['notam_number']:
                    notams.append(notam)

        except Exception as e:
            print(f"  XML 파싱 오류: {e}")

        return notams

    def save_notams(self, notams: List[Dict]) -> int:
        """NOTAM을 데이터베이스에 저장"""
        if not notams:
            return 0

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        saved_count = 0
        now = datetime.utcnow().isoformat()

        for notam in notams:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO notams (
                        notam_number, a_location, b_start_time, c_end_time,
                        d_schedule, e_text, f_lower_limit, g_upper_limit,
                        q_code, series_type, collected_at, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    notam['notam_number'],
                    notam['a_location'],
                    notam['b_start_time'],
                    notam['c_end_time'],
                    notam['d_schedule'],
                    notam['e_text'],
                    notam['f_lower_limit'],
                    notam['g_upper_limit'],
                    notam['q_code'],
                    notam['series_type'],
                    now,
                    now
                ))
                saved_count += 1
            except sqlite3.IntegrityError:
                # 이미 존재하는 NOTAM (업데이트됨)
                pass
            except Exception as e:
                print(f"  저장 오류: {e}")

        conn.commit()
        conn.close()

        return saved_count

    def run_sync(self, days_back: int = 30):
        """전체 동기화 실행"""
        print("="*60)
        print("NOTAM 초기 동기화 시작")
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"조회 기간: 최근 {days_back}일")
        print("="*60)
        print()

        all_notams = []
        total_saved = 0

        for airport in self.airports:
            print(f"[크롤링] {airport}...", end=' ', flush=True)

            notams = self.fetch_notams(airport, days_back)
            print(f"✅ {len(notams)}개", end=' ', flush=True)

            if notams:
                saved = self.save_notams(notams)
                total_saved += saved
                print(f"(저장: {saved}개)")
                all_notams.extend(notams)
            else:
                print()

            time.sleep(0.5)  # API 부하 방지

        print()
        print("="*60)
        print(f"✅ 동기화 완료!")
        print(f"총 수집: {len(all_notams)}개")
        print(f"DB 저장: {total_saved}개 (신규)")
        print("="*60)

        return total_saved


if __name__ == '__main__':
    import sys

    # 인자로 날짜 범위 지정 가능 (기본 30일)
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    crawler = NOTAMSyncCrawler()
    crawler.run_sync(days_back=days)
