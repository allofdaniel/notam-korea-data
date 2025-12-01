"""
대한민국 NOTAM 크롤러 - 실시간 항공고시보 데이터 수집
작성일: 2025-11-09
"""

import time
import sqlite3
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pytz
import logging
import sys
import os

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

class NOTAMCrawler:
    def __init__(self, db_name='notam_realtime.db', headless=True):
        self.url = 'https://aim.koca.go.kr/xNotam/?language=ko_KR#'
        self.db_name = db_name
        self.headless = headless  # 헤드리스 모드 옵션

        # 한국 공항 코드 (모두 18개)
        self.airports = [
            'RKSI', 'RKSS', 'RKPK', 'RKPC', 'RKPS', 'RKPU',
            'RKSM', 'RKTH', 'RKPD', 'RKTL', 'RKNW', 'RKJK',
            'RKJB', 'RKJY', 'RKJJ', 'RKTN', 'RKTU', 'RKNY'
        ]

        # NOTAM SERIES 타입
        self.series_types = ['A', 'C', 'D', 'E', 'G', 'Z', 'S', 'N', 'O', 'W', 'T', 'A', 'M']
        
        self.setup_database()
        logger.info("[OK] NOTAM 크롤러 초기화 완료")
        logger.info(f"[INFO] 공항 수: {len(self.airports)}개")
        logger.info(f"[INFO] SERIES 타입: {', '.join(self.series_types)}")
    
    def setup_database(self):
        """SQLite 데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # NOTAM 데이터 테이블
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
    
    def get_utc_time(self):
        """현재 UTC 시간 반환"""
        from datetime import timezone
        return datetime.now(timezone.utc).replace(tzinfo=None)
    
    def init_driver(self):
        """Chrome 드라이버 초기화"""
        options = webdriver.ChromeOptions()

        # 헤드리스 모드 설정 (옵션으로 제어 가능)
        if self.headless:
            options.add_argument('--headless')
            logger.info("[INFO] 헤드리스 모드 활성화")

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        return driver
    
    def click_airport_buttons(self, driver, is_international=False):
        """공항 선택 - 국내는 버튼 클릭, 국제는 텍스트 입력 또는 전체 선택"""
        logger.info("공항 선택 시작...")
        success_count = 0

        if is_international:
            # 국제 NOTAM: LOCATION 필드를 비워두거나 FIR 영역 입력
            try:
                # LOCATION 입력 필드 찾기 (여러 가능성 시도)
                location_selectors = [
                    "input[name='LOCATION']",
                    "input[name='location']",
                    "input[id*='location']",
                    "input[placeholder*='LOCATION']",
                    "textarea[name='LOCATION']"
                ]

                location_field = None
                for selector in location_selectors:
                    try:
                        location_field = driver.find_element(By.CSS_SELECTOR, selector)
                        if location_field:
                            break
                    except:
                        continue

                if location_field:
                    # LOCATION 필드를 비워두거나 'RK'(한국 FIR) 입력
                    driver.execute_script("arguments[0].value = '';", location_field)
                    logger.info(f"[OK] 국제 LOCATION 필드 설정 완료 (전체 검색)")
                    success_count = len(self.airports)
                else:
                    logger.warning("[WARN] 국제 LOCATION 입력 필드를 찾을 수 없음")
                    logger.info("[INFO] LOCATION 설정 없이 진행...")
                    success_count = len(self.airports)

            except Exception as e:
                logger.warning(f"[WARN] 국제 LOCATION 설정 실패: {e}")
                logger.info("[INFO] LOCATION 설정 없이 진행...")

        else:
            # 국내 NOTAM: JavaScript로 모든 버튼 일괄 클릭 (성능 최적화)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button.bt-sm"))
                )
            except TimeoutException:
                logger.warning("공항 선택 영역을 찾을 수 없습니다.")

            # JavaScript로 모든 공항 버튼 일괄 클릭
            click_script = """
            var airports = arguments[0];
            var successCount = 0;
            var buttons = document.querySelectorAll('button.bt-sm');

            buttons.forEach(function(btn) {
                var text = btn.textContent.trim();
                if (airports.includes(text)) {
                    btn.click();
                    successCount++;
                }
            });

            return successCount;
            """

            try:
                success_count = driver.execute_script(click_script, self.airports)
                logger.info(f"[OK] JavaScript로 공항 버튼 일괄 클릭: {success_count}개")
            except Exception as e:
                logger.warning(f"[WARN] JavaScript 일괄 클릭 실패: {e}, 개별 클릭 시도...")

                # Fallback: 개별 클릭
                for airport in self.airports:
                    try:
                        buttons = driver.find_elements(By.CSS_SELECTOR, "button.bt-sm")
                        for btn in buttons:
                            if btn.text.strip() == airport:
                                driver.execute_script("arguments[0].click();", btn)
                                success_count += 1
                                break
                    except Exception as e:
                        logger.warning(f"  [WARN] {airport} 버튼 클릭 실패: {e}")

        logger.info(f"공항 선택 완료: {success_count}/{len(self.airports)}")
    
    def click_series_buttons(self, driver):
        """모든 SERIES 버튼 클릭 (JavaScript 일괄 처리)"""
        logger.info("SERIES 버튼 클릭 시작...")

        # SNOWTAM 포함 모든 SERIES
        all_series = ['A', 'C', 'D', 'E', 'G', 'Z', 'SNOWTAM']

        # JavaScript로 모든 SERIES 버튼 일괄 클릭
        click_script = """
        var seriesList = arguments[0];
        var successCount = 0;
        var divs = document.querySelectorAll('div.mntype-block2');

        divs.forEach(function(div) {
            var link = div.querySelector('a');
            if (link) {
                var text = link.textContent.trim();
                if (seriesList.includes(text)) {
                    div.click();
                    successCount++;
                }
            }
        });

        return successCount;
        """

        try:
            success_count = driver.execute_script(click_script, all_series)
            logger.info(f"[OK] JavaScript로 SERIES 버튼 일괄 클릭: {success_count}/{len(all_series)}개")
        except Exception as e:
            logger.warning(f"[WARN] JavaScript 일괄 클릭 실패: {e}, 개별 클릭 시도...")

            # Fallback: 개별 클릭
            success_count = 0
            for series in all_series:
                try:
                    divs = driver.find_elements(By.CSS_SELECTOR, "div.mntype-block2")
                    for div in divs:
                        links = div.find_elements(By.TAG_NAME, "a")
                        if links and links[0].text.strip() == series:
                            driver.execute_script("arguments[0].click();", div)
                            success_count += 1
                            break
                except Exception as e:
                    logger.warning(f"  [WARN] {series} 버튼 클릭 실패: {e}")

        logger.info(f"SERIES 선택 완료: {success_count}/{len(all_series)}")
    
    def set_search_time(self, driver, hours_back=24):
        """검색 시간 설정 (UTC 기준, HHMM 형식)"""
        utc_now = self.get_utc_time()
        start_time = utc_now - timedelta(hours=hours_back)

        logger.info("검색 시간 설정 중...")

        try:
            # name 속성으로 직접 input 필드 찾기 (더 안정적)
            from_date = driver.find_element(By.NAME, "sch_from_date")
            from_time = driver.find_element(By.NAME, "sch_from_time")
            to_date = driver.find_element(By.NAME, "sch_to_date")
            to_time = driver.find_element(By.NAME, "sch_to_time")

            # 발행 시작 날짜
            driver.execute_script("arguments[0].value = arguments[1];",
                                 from_date, start_time.strftime("%Y-%m-%d"))
            logger.info(f"[OK] 시작 날짜: {start_time.strftime('%Y-%m-%d')}")

            # 발행 시작 시간 - HHMM 형식
            driver.execute_script("arguments[0].value = arguments[1];",
                                 from_time, start_time.strftime("%H%M"))
            logger.info(f"[OK] 시작 시간: {start_time.strftime('%H%M')}")

            # 발행 종료 날짜
            driver.execute_script("arguments[0].value = arguments[1];",
                                 to_date, utc_now.strftime("%Y-%m-%d"))
            logger.info(f"[OK] 종료 날짜: {utc_now.strftime('%Y-%m-%d')}")

            # 발행 종료 시간 - HHMM 형식
            driver.execute_script("arguments[0].value = arguments[1];",
                                 to_time, utc_now.strftime("%H%M"))
            logger.info(f"[OK] 종료 시간: {utc_now.strftime('%H%M')}")

            logger.info(f"[INFO] 검색 기간: {start_time.strftime('%Y-%m-%d %H%M')} ~ {utc_now.strftime('%Y-%m-%d %H%M')} UTC")
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"[ERROR] 시간 설정 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def extract_notam_data(self, driver):
        """테이블에서 NOTAM 데이터 추출 (IBSheet API 사용)"""
        notam_list = []

        try:
            # 테이블이 로드될 때까지 대기
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            time.sleep(2)

            # JavaScript로 IBSheet API를 사용하여 데이터 추출
            logger.info("IBSheet API를 사용하여 데이터 추출 중...")

            extract_script = """
            var result = [];
            try {
                // IBSheet 객체가 있는지 확인
                if (typeof Grids === 'undefined' || !Grids || Grids.length === 0) {
                    return {error: 'IBSheet not found'};
                }

                var grid = Grids[0];
                var rowCount = grid.GetDataRows ? grid.GetDataRows() : 0;

                console.log('IBSheet row count:', rowCount);

                for (var i = 1; i <= rowCount; i++) {
                    try {
                        var row = {
                            notam_type: grid.GetCellValue(i, 'C2') || '',      // TYPE
                            issue_time: grid.GetCellValue(i, 'C3') || '',      // ISSUE TIME
                            location: grid.GetCellValue(i, 'C4') || '',        // LOCATION
                            notam_no: grid.GetCellValue(i, 'C5') || '',        // NOTAM NO
                            qcode: grid.GetCellValue(i, 'C6') || '',           // QCODE
                            start_time: grid.GetCellValue(i, 'C7') || '',      // START TIME
                            end_time: grid.GetCellValue(i, 'C8') || '',        // END TIME
                            full_text: grid.GetCellValue(i, 'C9') || '',       // E)
                            full_text_detail: grid.GetCellValue(i, 'C10') || '' // F)
                        };

                        // NOTAM NO가 있는 행만 추가
                        if (row.notam_no && row.notam_no.trim() !== '') {
                            result.push(row);
                        }
                    } catch (e) {
                        console.error('Error extracting row', i, e);
                    }
                }

                return {data: result, count: rowCount};

            } catch (e) {
                return {error: e.toString()};
            }
            """

            extraction_result = driver.execute_script(extract_script)

            # 에러 체크
            if 'error' in extraction_result:
                logger.error(f"IBSheet API 에러: {extraction_result['error']}")
                logger.warning("Fallback: XPath 방식으로 재시도...")
                return self.extract_notam_data_fallback(driver)

            # 데이터 처리
            if 'data' in extraction_result:
                notam_list = extraction_result['data']
                logger.info(f"IBSheet에서 {len(notam_list)}개 NOTAM 추출 (총 {extraction_result.get('count', 0)}개 행)")

                # 디버그: 처음 3개 샘플 출력
                for idx, notam in enumerate(notam_list[:3], 1):
                    logger.debug(f"샘플 {idx}: TYPE={notam.get('notam_type')}, NO={notam.get('notam_no')}, LOC={notam.get('location')}")

        except Exception as e:
            logger.error(f"IBSheet 데이터 추출 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.warning("Fallback: XPath 방식으로 재시도...")
            return self.extract_notam_data_fallback(driver)

        return notam_list

    def extract_notam_data_fallback(self, driver):
        """Fallback: XPath를 사용한 데이터 추출 (IBSheet 실패 시)"""
        notam_list = []

        try:
            # 테이블 행 찾기 - nested table 고려하여 더 정확한 XPath 사용
            rows = driver.find_elements(By.XPATH, "//table[@id='sheetDiv_IBSheet']//tr[contains(@class, 'Row')]")

            if not rows:
                # 다른 방법으로 시도
                rows = driver.find_elements(By.XPATH, "//table//tbody//tr[td]")

            logger.info(f"Fallback: 테이블에서 {len(rows)}개 행 발견")

            for idx, row in enumerate(rows):
                try:
                    # 모든 td 요소 찾기
                    cells = row.find_elements(By.XPATH, ".//td")

                    logger.debug(f"행 {idx}: {len(cells)}개 셀 발견")

                    if len(cells) < 10:
                        continue

                    # 각 셀의 텍스트 출력 (디버깅용)
                    cell_texts = [cell.text.strip() for cell in cells[:11]]
                    logger.debug(f"행 {idx} 셀 내용: {cell_texts}")

                    # NOTAM NO 확인 (보통 5번째 또는 6번째 셀)
                    notam_no = None
                    notam_type = None

                    # 셀 인덱스를 유연하게 찾기
                    for i, text in enumerate(cell_texts):
                        if text and len(text) > 5 and any(char.isalpha() for char in text) and any(char.isdigit() for char in text):
                            # NOTAM 번호 형식으로 보이는 경우
                            if '/' in text or '-' in text:
                                notam_no = text
                                # TYPE은 보통 그 앞쪽에 있음
                                if i >= 2:
                                    notam_type = cell_texts[i-3] if i-3 >= 0 else ''
                                break

                    if not notam_no:
                        continue

                    # 헤더 행 제외
                    if 'NOTAM NO' in notam_no or 'TYPE' in notam_no:
                        continue

                    # 기본 인덱스로 시도 (조정 가능)
                    notam = {
                        'notam_type': cell_texts[2] if len(cell_texts) > 2 else notam_type or '',
                        'issue_time': cell_texts[3] if len(cell_texts) > 3 else '',
                        'location': cell_texts[4] if len(cell_texts) > 4 else '',
                        'notam_no': notam_no,
                        'qcode': cell_texts[6] if len(cell_texts) > 6 else '',
                        'start_time': cell_texts[7] if len(cell_texts) > 7 else '',
                        'end_time': cell_texts[8] if len(cell_texts) > 8 else '',
                        'full_text': cell_texts[9] if len(cell_texts) > 9 else '',
                        'full_text_detail': cell_texts[10] if len(cell_texts) > 10 else ''
                    }

                    notam_list.append(notam)
                    logger.debug(f"Fallback 행 {idx}: NOTAM 추가됨 - {notam_no}")

                except Exception as e:
                    logger.debug(f"Fallback 행 {idx} 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.error(f"Fallback 테이블 파싱 오류: {e}")

        logger.info(f"Fallback: {len(notam_list)}개 NOTAM 추출 완료")
        return notam_list
    
    def save_to_database(self, notam_list, data_source, crawl_timestamp):
        """NOTAM 데이터를 DB에 저장"""
        if not notam_list:
            return 0
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        saved_count = 0
        
        for notam in notam_list:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO notam_records 
                    (crawl_timestamp, data_source, notam_type, issue_time, location, 
                     notam_no, qcode, start_time, end_time, full_text, full_text_detail)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    crawl_timestamp, data_source, notam['notam_type'], 
                    notam['issue_time'], notam['location'], notam['notam_no'],
                    notam['qcode'], notam['start_time'], notam['end_time'],
                    notam['full_text'], notam['full_text_detail']
                ))
                if cursor.rowcount > 0:
                    saved_count += 1
            except Exception as e:
                logger.error(f"DB 저장 오류: {e}")
        
        conn.commit()
        conn.close()
        return saved_count
    
    def log_crawl(self, crawl_timestamp, data_source, status, records_found, 
                  records_saved, error_message=None, execution_time=0):
        """크롤링 로그 저장"""
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
    
    def close_modal_if_exists(self, driver):
        """모달 창이 있으면 닫기"""
        try:
            # 모달이 나타날 때까지 잠시 대기
            time.sleep(1.5)

            # JavaScript로 모달 강제 닫기
            driver.execute_script("""
                // Bootstrap 모달 닫기
                if (typeof $ !== 'undefined' && $('.modal').length > 0) {
                    $('.modal').modal('hide');
                }
                // 모달 배경 제거
                $('.modal-backdrop').remove();
                $('body').removeClass('modal-open');
            """)
            time.sleep(0.5)

            # Close 버튼 클릭 시도 (짧은 대기)
            close_selectors = [
                "//div[@class='modal-footer']//a[contains(text(), 'Close')]",
                "//a[@data-dismiss='modal']"
            ]

            for selector in close_selectors:
                try:
                    close_btn = driver.find_element(By.XPATH, selector)
                    driver.execute_script("arguments[0].click();", close_btn)
                    logger.info("[OK] 모달 Close 버튼 클릭")
                    time.sleep(0.5)
                    return True
                except:
                    continue

            logger.info("[OK] 모달 처리 완료")
            return True

        except Exception as e:
            logger.warning(f"[WARN] 모달 처리 중 오류: {e}")
            return False

    def crawl_notam(self, data_source='domestic', hours_back=24):
        """NOTAM 크롤링 실행"""
        driver = None
        start_time = time.time()
        crawl_timestamp = datetime.now().isoformat()

        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"[START] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {data_source.upper()} NOTAM 크롤링 시작")
            logger.info(f"{'='*70}")

            driver = self.init_driver()
            driver.get(self.url)
            time.sleep(2)  # 페이지 로딩 대기

            # 모달 창 닫기
            self.close_modal_if_exists(driver)

            # 국내/국제 탭 선택
            if data_source == 'international':
                try:
                    # 국제 탭 클릭 시도
                    intl_selectors = [
                        "//label[contains(text(), '국제')]",
                        "//input[@value='international']",
                        "//span[contains(text(), '국제')]"
                    ]

                    clicked = False
                    for selector in intl_selectors:
                        try:
                            intl_tab = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            intl_tab.click()
                            clicked = True
                            break
                        except:
                            continue

                    if clicked:
                        logger.info("[OK] 국제 탭 선택")
                    else:
                        logger.warning("[WARN] 국제 탭 선택 실패")

                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"[WARN] 국제 탭 선택 실패: {e}")
            else:
                logger.info("[OK] 국내 탭 선택 (기본)")

            # 모든 공항 선택
            logger.info(f"[INFO] 공항 선택 중... ({len(self.airports)}개)")
            is_intl = (data_source == 'international')
            self.click_airport_buttons(driver, is_international=is_intl)

            # 모든 SERIES 선택
            logger.info(f"[INFO] SERIES 선택 중...")
            self.click_series_buttons(driver)

            # 검색 시간 설정
            self.set_search_time(driver, hours_back=hours_back)
            
            # 검색 실행
            try:
                search_btn = driver.find_element(By.CSS_SELECTOR, "a.btn-primary")
                driver.execute_script("arguments[0].click();", search_btn)
                logger.info("[OK] 검색 버튼 클릭")
            except Exception as e:
                logger.error(f"[ERROR] 검색 버튼 클릭 실패: {e}")
                raise Exception("검색 버튼을 찾을 수 없습니다.")

            # 결과 로딩 대기
            logger.info("검색 결과 로딩 중...")
            time.sleep(3)
            
            # 데이터 추출
            notam_list = self.extract_notam_data(driver)
            logger.info(f"[INFO] 추출된 NOTAM: {len(notam_list)}개")
            
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
            
            logger.info(f"\n[OK] 크롤링 완료 - 실행시간: {execution_time:.2f}초")
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
        
        finally:
            if driver:
                driver.quit()
    
    def test_crawl(self):
        """테스트 크롤링 실행"""
        logger.info("[TEST] 테스트 크롤링 시작...")

        # 국내 NOTAM 테스트만 (임시)
        domestic_result = self.crawl_notam('domestic')

        # 국제 NOTAM 테스트 - 임시로 비활성화
        # international_result = self.crawl_notam('international')

        return {
            'domestic': domestic_result,
            # 'international': international_result
        }

def main():
    """메인 실행 함수"""
    crawler = NOTAMCrawler()
    
    # 테스트 실행
    results = crawler.test_crawl()
    
    # 결과 출력
    print("\n" + "="*70)
    print("[SUMMARY] 테스트 결과 요약")
    print("="*70)
    
    for data_source, result in results.items():
        print(f"\n[TEST] {data_source.upper()} NOTAM:")
        if result['status'] == 'SUCCESS':
            print(f"  [OK] 성공 - {result['records_found']}개 발견, {result['records_saved']}개 저장")
            print(f"  [TIME] 실행시간: {result['execution_time']:.2f}초")
        else:
            print(f"  [FAIL] 실패 - {result['error']}")
            print(f"  [TIME] 실행시간: {result['execution_time']:.2f}초")

if __name__ == "__main__":
    main()