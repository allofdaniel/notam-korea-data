# NOTAM Complete 데이터 가이드 (FULL_TEXT 포함)

## 📁 저장된 파일

### 위치
```
C:\Users\allof\Desktop\code
```

### 파일 목록
1. **notam_final_complete.db** (86.46 MB)
   - SQLite 데이터베이스
   - 154,986개 레코드
   - **FULL_TEXT 포함** (완전한 노탐 정보)

2. **notam_final_complete.json** (120.95 MB)
   - JSON 형식
   - 154,986개 레코드
   - **FULL_TEXT 포함**

## 📊 데이터 통계

- **총 레코드**: 154,986개
- **기간**: 2022-2025년
- **중복**: 없음 (UNIQUE 제약)
- **FULL_TEXT**: 100% (154,986개 모두 포함)

### 연도별
- 2022:  4,449개
- 2023: 51,925개
- 2024: 51,742개
- 2025: 46,870개

### 시리즈별 Top 10
- A (Airport): 64,970개
- E (Restricted): 17,404개
- C (Communications): 12,962개
- D (Danger): 11,929개
- S (Snow): 6,393개
- B (Bearing): 5,120개
- J: 4,253개
- Z (Conditional): 4,104개
- G (General): 3,289개

## 🔍 데이터 보기/검색

### 1. 빠른 확인
```bash
py view_complete_data.py
```

### 2. 검색
```bash
# 키워드 검색
py search_complete_notam.py "RWY"

# 대화형 검색
py search_complete_notam.py
```

### 3. Python으로 직접 조회
```python
import sqlite3

conn = sqlite3.connect('notam_final_complete.db')
cursor = conn.cursor()

# 2024년 데이터만
cursor.execute("SELECT * FROM notams WHERE year = 2024 LIMIT 10")
for row in cursor.fetchall():
    print(row)

# FULL_TEXT로 검색
cursor.execute("SELECT * FROM notams WHERE full_text LIKE '%RUNWAY%' LIMIT 10")
for row in cursor.fetchall():
    print(row[10])  # full_text 필드

conn.close()
```

### 4. JSON 파일 읽기
```python
import json

with open('notam_final_complete.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 첫 10개
for notam in data[:10]:
    print(notam['notam_number'], notam['location'])
    print(notam['full_text'][:100])  # FULL_TEXT 미리보기

# FULL_TEXT로 검색
runway_notams = [n for n in data if 'RWY' in (n.get('full_text') or '')]
print(f"RWY 포함 NOTAM: {len(runway_notams)}개")
```

## 🗃️ 데이터베이스 스키마

```sql
CREATE TABLE notams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notam_number TEXT,           -- NOTAM 번호
    location TEXT,               -- 공항/위치 코드
    series TEXT,                 -- 시리즈 (A/C/D/E/G/Z 등)
    qcode TEXT,                  -- Q 코드
    qcode_mean TEXT,             -- Q 코드 의미
    issue_time TEXT,             -- 발행 시간
    effective_start TEXT,        -- 시작 시간
    effective_end TEXT,          -- 종료 시간
    e_text TEXT,                 -- 본문 (간략)
    full_text TEXT,              -- **완전한 NOTAM 텍스트** (NEW!)
    fir TEXT,                    -- FIR 코드
    ais_type TEXT,               -- AIS 타입
    crawl_date TEXT,             -- 크롤링 날짜
    year INTEGER,                -- 연도
    UNIQUE(notam_number, location, effective_start, effective_end)
)
```

## 🆕 FULL_TEXT 필드

**완전한 NOTAM 정보가 포함된 필드**

예시:
```
GG RKZZNAXX
012232 RKRRYNYX
(A1728/22 NOTAMN
Q)RKRR/QCPAS/I/BO/A/000/999/3643N12730E005
A)RKTU B)2212070400 C)2212070700
E)PAR RWY 06L/24R, RWY 06R/24L U/S DUE TO MAINT)
```

- 모든 레코드(154,986개)에 FULL_TEXT 포함 (100%)
- 원본 NOTAM 형식 그대로 저장
- 항공 정보, 좌표, 시간, 상세 내용 모두 포함

## 🛠️ 도구

### 설치된 스크립트
- `view_complete_data.py` - 데이터 통계 확인 (FULL_TEXT 샘플 포함)
- `search_complete_notam.py` - NOTAM 검색 (FULL_TEXT 검색 가능)
- `merge_complete_data.py` - Worker DB 병합 (이미 실행됨)

### SQLite Browser (권장)
무료 GUI 도구: https://sqlitebrowser.org/

## ☁️ S3 업로드

AWS 인증 설정 후:
```bash
py upload_complete_to_s3.py
```

업로드 대상:
- `notam-korea-data` 버킷
- `notam-backup` 버킷

## 📝 예제 쿼리

### FULL_TEXT로 활주로 관련 NOTAM 검색
```sql
SELECT notam_number, location, full_text
FROM notams
WHERE full_text LIKE '%RUNWAY%' OR full_text LIKE '%RWY%'
LIMIT 10
```

### 특정 공항의 FULL_TEXT
```sql
SELECT notam_number, full_text
FROM notams
WHERE location = 'RKSI'  -- 인천공항
ORDER BY effective_start DESC
LIMIT 10
```

### 2024년 가장 긴 NOTAM (FULL_TEXT 기준)
```sql
SELECT notam_number, location, LENGTH(full_text) as len, full_text
FROM notams
WHERE year = 2024
ORDER BY len DESC
LIMIT 5
```

### 최근 1주일 NOTAM (FULL_TEXT 포함)
```sql
SELECT notam_number, location, full_text
FROM notams
WHERE crawl_date >= date('now', '-7 days')
ORDER BY crawl_date DESC
```

## ✅ 데이터 검증

- ✅ 총 154,986개 레코드 수집
- ✅ FULL_TEXT 100% 포함 (0개 누락)
- ✅ 2022-2025년 모든 데이터
- ✅ 국내 + 국제 노탐 모두 포함
- ✅ 모든 공항, 모든 시리즈 타입
- ✅ 중복 제거 완료 (243개 중복 제거됨)

## 📈 이전 버전과의 차이

| 항목 | 이전 (notam_final_all.db) | 현재 (notam_final_complete.db) |
|------|--------------------------|-------------------------------|
| 레코드 수 | 154,908개 | 154,986개 |
| FULL_TEXT | ❌ 없음 | ✅ 100% 포함 |
| 필드 수 | 12개 | 15개 |
| 완전한 정보 | ❌ 부분적 | ✅ 완전함 |
| 파일 크기 (DB) | 10.45 MB | 86.46 MB |
| 파일 크기 (JSON) | 44.79 MB | 120.95 MB |

## 🎯 주요 개선 사항

1. **FULL_TEXT 필드 추가** - 완전한 NOTAM 정보 저장
2. **추가 메타데이터** - qcode_mean, issue_time, fir, ais_type 등
3. **더 정확한 시간 정보** - effective_start/end vs b_start_time/c_end_time
4. **완전성 보장** - 모든 레코드에 FULL_TEXT 포함

## 🚀 다음 단계

1. 로컬에서 데이터 확인:
   ```bash
   py view_complete_data.py
   py search_complete_notam.py "YOUR_KEYWORD"
   ```

2. S3에 업로드:
   ```bash
   py upload_complete_to_s3.py
   ```

3. 데이터 활용:
   - 항공 안전 분석
   - NOTAM 트렌드 분석
   - 공항별 통계
   - 시계열 분석
