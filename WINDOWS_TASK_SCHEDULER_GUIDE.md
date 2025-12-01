# Windows Task Scheduler 자동 크롤러 설정 가이드

## 🎯 목표

5분마다 자동으로 NOTAM 크롤링 → DynamoDB 업로드

---

## 📋 사전 준비

✅ `auto_crawler_to_cloud.py` 스크립트 생성 완료
✅ AWS CLI 설정 완료 (`aws configure`)
✅ Python 설치 및 필요한 패키지 설치 완료

---

## 🔧 설정 방법

### **Step 1: 배치 파일 생성**

`C:\Users\allof\Desktop\code\run_crawler.bat` 파일 생성:

```batch
@echo off
cd /d C:\Users\allof\Desktop\code
python auto_crawler_to_cloud.py >> crawler_log.txt 2>&1
```

**설명:**
- `cd /d C:\Users\allof\Desktop\code`: 작업 디렉토리로 이동
- `python auto_crawler_to_cloud.py`: 크롤러 실행
- `>> crawler_log.txt 2>&1`: 출력 로그를 파일에 저장

---

### **Step 2: Windows Task Scheduler 열기**

1. **Windows 키** + **R** → `taskschd.msc` 입력 → **Enter**
2. 또는: 시작 메뉴 → "작업 스케줄러" 검색

---

### **Step 3: 새 작업 만들기**

1. **작업 스케줄러** 우측 패널 → **기본 작업 만들기** 클릭

2. **이름 및 설명**
   - 이름: `NOTAM Auto Crawler`
   - 설명: `5분마다 NOTAM 데이터 자동 수집 및 DynamoDB 업로드`

3. **트리거** (실행 시기)
   - "매일" 선택 → **다음**
   - 시작 날짜: 오늘
   - 시작 시간: 현재 시간
   - **다음**

4. **작업**
   - "프로그램 시작" 선택 → **다음**
   - **프로그램/스크립트**: `C:\Users\allof\Desktop\code\run_crawler.bat`
   - **다음**

5. **마침**
   - "마침을 클릭할 때 작업 속성 대화 상자 열기" 체크
   - **마침**

---

### **Step 4: 고급 설정 (5분 간격 실행)**

**속성 대화 상자**가 열리면:

1. **트리거** 탭
   - 트리거 선택 → **편집** 클릭
   - **고급 설정**에서:
     - ✅ "반복 간격" 체크
     - 간격: **5분**
     - 기간: **무기한**
   - **확인**

2. **조건** 탭
   - ❌ "컴퓨터가 AC 전원에 있을 때만 작업 시작" 해제
   - ❌ "컴퓨터의 AC 전원이 분리되면 중지" 해제

3. **설정** 탭
   - ✅ "작업이 실패하면 다시 시작 간격" 체크: **1분**
   - ✅ "작업을 요청 시 실행할 수 있음" 체크

4. **확인**

---

## ✅ 테스트

### 수동 실행 테스트

1. **작업 스케줄러**에서 `NOTAM Auto Crawler` 우클릭
2. **실행** 클릭
3. `C:\Users\allof\Desktop\code\crawler_log.txt` 확인

### 로그 확인

```bash
# PowerShell에서:
Get-Content C:\Users\allof\Desktop\code\crawler_log.txt -Tail 50
```

---

## 📊 모니터링

### 크롤링 로그 확인

```bash
# 최근 로그 확인
type C:\Users\allof\Desktop\code\crawler_log.txt
```

### DynamoDB 데이터 확인

```bash
aws dynamodb scan --table-name NOTAM_Records --limit 10 --region ap-southeast-2
```

### API로 확인

```
https://402p7v6m12.execute-api.ap-southeast-2.amazonaws.com/prod/notams?data_source=domestic&limit=10
```

---

## 🛑 중지/삭제

### 일시 중지

1. **작업 스케줄러** → `NOTAM Auto Crawler` 우클릭
2. **사용 안 함** 클릭

### 완전 삭제

1. **작업 스케줄러** → `NOTAM Auto Crawler` 우클릭
2. **삭제** 클릭

---

## 💰 비용 계산 (로컬 방식)

| 항목 | 비용 |
|------|------|
| Lambda 크롤러 | $0 (사용 안 함) |
| DynamoDB | ~$5-10/월 |
| API Gateway | ~$3-5/월 |
| S3 | $0 (백업 안 함) |
| **총 예상 비용** | **~$10-15/월** |

**Lambda 대신 로컬 크롤러 사용 시 절약:**
- Lambda 실행 비용 $0
- S3 저장 비용 $0

---

## 🚨 문제 해결

### 작업이 실행되지 않는 경우

1. **배치 파일 경로 확인**
   - `C:\Users\allof\Desktop\code\run_crawler.bat` 존재 여부

2. **Python 경로 확인**
   ```batch
   # run_crawler.bat 수정:
   C:\Python311\python.exe auto_crawler_to_cloud.py >> crawler_log.txt 2>&1
   ```

3. **AWS 자격 증명 확인**
   ```bash
   aws sts get-caller-identity --region ap-southeast-2
   ```

### 오류 로그 확인

```bash
type C:\Users\allof\Desktop\code\crawler_error.log
```

---

## ✨ 완료!

이제 5분마다 자동으로:
1. NOTAM 데이터 크롤링
2. SQLite에 저장
3. DynamoDB에 업로드
4. API로 접근 가능

**최종 구조:**

```
사용자
  ↓
v0 대시보드 (Vercel)
  ↓ API 호출
AWS API Gateway
  ↓
Lambda API 함수
  ↓
DynamoDB (NOTAM 데이터)
  ↑
로컬 자동 크롤러 (5분마다)
  ↑
AIM 포털 API
```

**비용: ~$10-15/월** (국내 NOTAM 전용, 완전 자동화)
