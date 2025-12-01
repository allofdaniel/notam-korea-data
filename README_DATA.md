# NOTAM 데이터 사용 가이드

## 📁 저장된 파일

### 위치
```
C:\Users\allof\Desktop\code
```

### 파일 목록
1. **notam_final_all.db** (10.45 MB)
   - SQLite 데이터베이스
   - 154,908개 레코드

2. **notam_final_all.json** (44.79 MB)
   - JSON 형식
   - 154,908개 레코드

## 📊 데이터 통계

- **총 레코드**: 154,908개
- **기간**: 2022-2025년
- **중복**: 없음 (UNIQUE 제약)

### 연도별
- 2022:  4,490개
- 2023: 51,866개
- 2024: 51,714개
- 2025: 46,838개

## 🔍 데이터 보기/검색

### 1. 빠른 확인
```bash
py view_data.py
```

### 2. 검색
```bash
# 키워드 검색
py search_notam.py "RWY"

# 대화형 검색
py search_notam.py
```

### 3. Python으로 직접 조회
```python
import sqlite3

conn = sqlite3.connect('notam_final_all.db')
cursor = conn.cursor()

# 2024년 데이터만
cursor.execute("SELECT * FROM notams WHERE year = 2024 LIMIT 10")
for row in cursor.fetchall():
    print(row)

# 특정 공항
cursor.execute("SELECT * FROM notams WHERE a_location = 'RKSI' LIMIT 10")
for row in cursor.fetchall():
    print(row)

conn.close()
```

### 4. JSON 파일 읽기
```python
import json

with open('notam_final_all.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 첫 10개
for notam in data[:10]:
    print(notam['notam_number'], notam['a_location'])

# 특정 연도만
notams_2024 = [n for n in data if n['year'] == 2024]
print(f"2024: {len(notams_2024)}개")
```

## 🗃️ 데이터베이스 스키마

```sql
CREATE TABLE notams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notam_number TEXT,           -- NOTAM 번호
    a_location TEXT,             -- 공항/위치 코드
    b_start_time TEXT,           -- 시작 시간
    c_end_time TEXT,             -- 종료 시간
    e_text TEXT,                 -- 본문
    f_lower_limit TEXT,          -- 하한 고도
    g_upper_limit TEXT,          -- 상한 고도
    q_code TEXT,                 -- Q 코드
    series_type TEXT,            -- 시리즈 타입
    crawl_date TEXT,             -- 크롤링 날짜
    year INTEGER,                -- 연도
    UNIQUE(notam_number, a_location, b_start_time, c_end_time)
)
```

## 🛠️ 도구

### 설치된 스크립트
- `view_data.py` - 데이터 통계 확인
- `search_notam.py` - NOTAM 검색
- `check_data.py` - 데이터 검증

### SQLite Browser (권장)
무료 GUI 도구: https://sqlitebrowser.org/

## ☁️ S3 업로드

AWS 인증 설정 후:
```bash
py upload_to_s3_final.py
```

## 📝 예제 쿼리

### 가장 많은 NOTAM을 가진 공항 Top 10
```sql
SELECT a_location, COUNT(*) as cnt 
FROM notams 
GROUP BY a_location 
ORDER BY cnt DESC 
LIMIT 10
```

### 2024년 시리즈별 통계
```sql
SELECT series_type, COUNT(*) as cnt 
FROM notams 
WHERE year = 2024 
GROUP BY series_type 
ORDER BY cnt DESC
```

### 최근 1주일 NOTAM
```sql
SELECT * FROM notams 
WHERE crawl_date >= date('now', '-7 days') 
ORDER BY crawl_date DESC
```
