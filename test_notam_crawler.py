"""
NOTAM 크롤러 테스트 스크립트
"""

import sqlite3
from notam_crawler import NOTAMCrawler
import logging
import sys
import os

# Windows 한국어 환경 인코딩 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_database_setup():
    """데이터베이스 설정 테스트"""
    print("\n[TEST] 데이터베이스 설정 테스트...")
    crawler = NOTAMCrawler('test_notam.db')
    
    # 테이블 존재 확인
    conn = sqlite3.connect('test_notam.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    expected_tables = ['notam_records', 'crawl_logs']
    existing_tables = [table[0] for table in tables]
    
    print(f"생성된 테이블: {existing_tables}")
    
    for table in expected_tables:
        if table in existing_tables:
            print(f"  [OK] {table} 테이블 생성 완료")
        else:
            print(f"  [FAIL] {table} 테이블 생성 실패")
    
    conn.close()

def test_time_formatting():
    """시간 형식 테스트"""
    print("\n[TEST] 시간 형식 테스트...")
    crawler = NOTAMCrawler('test_notam.db')
    
    utc_time = crawler.get_utc_time()
    
    # 날짜 형식 테스트 (YYYY-MM-DD)
    date_format = utc_time.strftime("%Y-%m-%d")
    print(f"날짜 형식: {date_format}")
    
    # 시간 형식 테스트 (HH:MM)
    time_format = utc_time.strftime("%H:%M")
    print(f"시간 형식: {time_format}")
    
    # 형식 검증
    if len(date_format) == 10 and date_format.count('-') == 2:
        print("  [OK] 날짜 형식 올바름")
    else:
        print("  [FAIL] 날짜 형식 오류")
    
    if len(time_format) == 5 and time_format.count(':') == 1:
        print("  [OK] 시간 형식 올바름")
    else:
        print("  [FAIL] 시간 형식 오류")

def test_airport_codes():
    """공항 코드 테스트"""
    print("\n[TEST] 공항 코드 테스트...")
    crawler = NOTAMCrawler('test_notam.db')
    
    expected_airports = [
        'RKSI', 'RKSS', 'RKPK', 'RKPC', 'RKPS', 'RKPU', 
        'RKSM', 'RKTH', 'RKPD', 'RKTL', 'RKNW', 'RKJK', 
        'RKJB', 'RKJY', 'RKJJ', 'RKTN', 'RKTU', 'RKNY'
    ]
    
    print(f"설정된 공항 코드: {len(crawler.airports)}개")
    
    missing_airports = []
    for airport in expected_airports:
        if airport in crawler.airports:
            print(f"  [OK] {airport}")
        else:
            print(f"  [FAIL] {airport} - 누락")
            missing_airports.append(airport)
    
    if not missing_airports:
        print("  [OK] 모든 공항 코드 확인 완료")
    else:
        print(f"  [FAIL] 누락된 공항: {missing_airports}")

def test_series_codes():
    """SERIES 코드 테스트"""
    print("\n[TEST] SERIES 코드 테스트...")
    crawler = NOTAMCrawler('test_notam.db')
    
    # SNOWTAM 분해 확인
    expected_series = ['A', 'C', 'D', 'E', 'G', 'Z', 'SNOWTAM']
    actual_series = ['A', 'C', 'D', 'E', 'G', 'Z', 'SNOWTAM']
    
    print(f"SERIES 타입: {actual_series}")
    
    for series in expected_series:
        if series in actual_series:
            print(f"  [OK] {series}")
        else:
            print(f"  [FAIL] {series} - 누락")
    
    print("  [OK] SNOWTAM 별도 처리 확인")

def view_database_contents():
    """데이터베이스 내용 확인"""
    print("\n[INFO] 데이터베이스 내용 확인...")
    
    try:
        conn = sqlite3.connect('test_notam.db')
        cursor = conn.cursor()
        
        # NOTAM 레코드 확인
        cursor.execute("SELECT COUNT(*) FROM notam_records")
        notam_count = cursor.fetchone()[0]
        print(f"NOTAM 레코드: {notam_count}개")
        
        if notam_count > 0:
            cursor.execute("""
                SELECT data_source, COUNT(*) 
                FROM notam_records 
                GROUP BY data_source
            """)
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]}개")
            
            # 최근 5개 레코드 출력
            cursor.execute("""
                SELECT notam_no, location, notam_type, start_time, end_time 
                FROM notam_records 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            print("\n최근 NOTAM 데이터:")
            for row in cursor.fetchall():
                print(f"  {row[0]} - {row[1]} ({row[2]}) {row[3]}~{row[4]}")
        
        # 크롤링 로그 확인
        cursor.execute("SELECT COUNT(*) FROM crawl_logs")
        log_count = cursor.fetchone()[0]
        print(f"\n크롤링 로그: {log_count}개")
        
        if log_count > 0:
            cursor.execute("""
                SELECT data_source, status, records_found, records_saved, execution_time
                FROM crawl_logs 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            print("최근 크롤링 로그:")
            for row in cursor.fetchall():
                print(f"  {row[0]} - {row[1]} ({row[2]}개 발견, {row[3]}개 저장, {row[4]:.2f}초)")
        
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] 데이터베이스 확인 오류: {e}")

def run_quick_test():
    """빠른 테스트 실행 (실제 크롤링 없이)"""
    print("NOTAM 크롤러 빠른 테스트 시작")
    print("="*50)
    
    test_database_setup()
    test_time_formatting()
    test_airport_codes()
    test_series_codes()
    
    print("\n[OK] 빠른 테스트 완료")

def run_full_test():
    """전체 테스트 실행 (실제 크롤링 포함)"""
    print("NOTAM 크롤러 전체 테스트 시작")
    print("="*50)
    
    # 기본 테스트
    run_quick_test()
    
    print("\n[INFO] 실제 크롤링 테스트 시작...")
    print("[WARNING] 이 작업은 몇 분이 소요될 수 있습니다.")
    
    # 실제 크롤링 테스트
    crawler = NOTAMCrawler('test_notam.db')
    
    # 국내 NOTAM만 먼저 테스트
    print("\n[TEST] 국내 NOTAM 테스트...")
    domestic_result = crawler.crawl_notam('domestic')
    
    if domestic_result['status'] == 'SUCCESS':
        print(f"[OK] 국내 NOTAM 성공: {domestic_result['records_found']}개 발견")
        
        # 성공했다면 국제 NOTAM도 테스트
        print("\n[TEST] 국제 NOTAM 테스트...")
        intl_result = crawler.crawl_notam('international')
        
        if intl_result['status'] == 'SUCCESS':
            print(f"[OK] 국제 NOTAM 성공: {intl_result['records_found']}개 발견")
        else:
            print(f"[FAIL] 국제 NOTAM 실패: {intl_result.get('error', '알 수 없는 오류')}")
    else:
        print(f"[FAIL] 국내 NOTAM 실패: {domestic_result.get('error', '알 수 없는 오류')}")
    
    # 결과 확인
    view_database_contents()
    
    print("\n[OK] 전체 테스트 완료")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'full':
        run_full_test()
    else:
        run_quick_test()
        print("\n[INFO] 전체 테스트를 원한다면: python test_notam_crawler.py full")