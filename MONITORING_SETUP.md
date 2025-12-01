# 자동 감지 및 알림 시스템 설정 가이드

**목적**: 코드 구조 변경을 자동으로 감지하고 이메일로 알림 받기

---

## 🎯 시스템 개요

```
AIM 포털 구조 변경
    ↓
Lambda 크롤러 (자동 감지)
    ↓
CloudWatch Logs + SNS 알림
    ↓
이메일로 알림 수신
    ↓
사용자가 코드 수동 수정
```

---

## 📋 설정 단계

### STEP 1: SNS 토픽 생성 (5분)

#### 1.1 SNS 콘솔 접속
1. AWS 콘솔 → SNS 검색
2. "주제" → "주제 생성"

#### 1.2 주제 설정
```
유형: 표준

이름: notam-crawler-alerts

표시 이름: NOTAM 크롤러 알림
```

3. [주제 생성] 클릭
4. **ARN 복사** (예: arn:aws:sns:ap-northeast-2:123456789012:notam-crawler-alerts)

#### 1.3 구독 생성
1. 생성된 주제 클릭
2. "구독 생성" 클릭
3. 설정:
   ```
   프로토콜: 이메일
   엔드포인트: your-email@example.com
   ```
4. [구독 생성] 클릭
5. **이메일 확인** (받은 편지함에서 확인 링크 클릭)

---

### STEP 2: Lambda 함수 업데이트

#### 2.1 개선된 크롤러 코드 배포

**로컬에서**:
```powershell
cd C:\Users\allof\Desktop\code

# 개선 버전으로 교체
Copy-Item lambda_crawler_with_monitoring.py lambda_crawler.py -Force

# 재패키징
.\deploy_to_aws.ps1
```

#### 2.2 Lambda 환경 변수 추가

1. Lambda 함수 `notam-crawler` → "구성" → "환경 변수"
2. 추가:
   ```
   SNS_TOPIC_ARN = arn:aws:sns:ap-northeast-2:123456789012:notam-crawler-alerts
   ```

#### 2.3 IAM 권한 추가

1. Lambda 함수 → "구성" → "권한"
2. 역할 클릭 → "권한 추가" → "정책 연결"
3. `AmazonSNSFullAccess` 추가

---

### STEP 3: CloudWatch 알람 설정 (알림 강화)

#### 3.1 오류 알람

1. CloudWatch → "경보" → "경보 생성"
2. 지표 선택:
   ```
   네임스페이스: AWS/Lambda
   지표 이름: Errors
   함수 이름: notam-crawler
   ```
3. 조건:
   ```
   임계값 유형: 정적
   조건: 보다 큼
   임계값: 0  (오류 1개 이상 발생 시)
   ```
4. 작업:
   ```
   알림 전송: notam-crawler-alerts (SNS 토픽)
   ```

#### 3.2 연속 실패 알람

1. "경보 생성"
2. 지표:
   ```
   Errors (합계)
   기간: 5분
   ```
3. 조건:
   ```
   조건: 보다 큼
   임계값: 3  (5분 동안 3회 이상 실패)
   ```

---

## 📧 알림 예시

### 알림 1: 구조 변경 감지
```
제목: [NOTAM 크롤러] API 구조 변경 감지

내용:
NOTAM API의 응답 구조 변경이 감지되었습니다.

감지된 변경:
- 필드명 변경: notam_id → AIS_NUM → NOTAM_NUMBER

현재는 자동으로 대응했지만, 코드 검토를 권장합니다.

확인 위치: lambda_crawler.py FIELD_MAPPINGS
시간: 2025-11-11 14:30:00 UTC
```

### 알림 2: 연속 실패
```
제목: [NOTAM 크롤러] 크롤링 연속 실패

내용:
NOTAM 크롤러가 3회 연속 실패했습니다.

가능한 원인:
1. API URL 변경
2. API 페이로드 구조 변경
3. 네트워크 문제

조치: lambda_crawler.py 코드 확인 필요
시간: 2025-11-11 14:35:00 UTC
```

---

## 🔍 개선된 코드의 장점

### 1. 유연한 필드 매핑
**기존 코드**:
```python
'notam_id': record.get('AIS_NUM', '')  # 고정
```

**개선 코드**:
```python
# 여러 가능한 필드명 자동 시도
'notam_id': self.get_field_value(record, 'notam_id')
# 'AIS_NUM', 'NOTAM_NUM', 'NOTAM_NO', 'NUM' 순서로 시도
```

### 2. 다중 URL 지원
```python
self.api_urls = [
    "https://aim.koca.go.kr/apisvc/getIBSheetData.do",
    # 백업 URL 추가 가능
]
```

### 3. 자동 알림
- 연속 3회 실패 시 → 이메일 알림
- 구조 변경 감지 시 → 이메일 알림
- CloudWatch 오류 발생 시 → 이메일 알림

---

## ⚠️ 한계

### 여전히 수동 수정이 필요한 경우

1. **완전히 새로운 API 엔드포인트**
   - 예: `/apisvc/getIBSheetData.do` → `/api/v2/notam`
   - → 코드에 새 URL 추가 필요

2. **전혀 다른 응답 구조**
   - 예: JSON → XML 변경
   - → 파싱 로직 전면 수정 필요

3. **인증 방식 추가**
   - 예: API 키, OAuth 필요
   - → 인증 로직 추가 필요

4. **페이로드 필드 전면 변경**
   - 예: `inorout`, `startdate` 등 10개 필드 모두 변경
   - → 페이로드 생성 로직 수정 필요

---

## 💡 권장 운영 방식

### 정상 운영 시
1. 1분마다 자동 크롤링 ✓
2. CloudWatch Logs 자동 수집 ✓
3. 오류 발생 시 이메일 알림 ✓

### 알림 수신 시
1. **즉시**: CloudWatch Logs 확인
   ```
   Lambda → 모니터 → CloudWatch의 로그 보기
   ```

2. **5분 이내**: 오류 원인 파악
   - 네트워크 일시 오류? → 자동 복구 대기
   - 구조 변경? → 코드 수정 준비

3. **30분 이내**: 코드 수정 (필요 시)
   - `lambda_crawler.py` 수정
   - 재배포: `.\deploy_to_aws.ps1`
   - Lambda 함수 업데이트

4. **테스트 및 모니터링**
   - Lambda 테스트 실행
   - CloudWatch Logs 확인
   - 정상화 여부 확인

---

## 📊 비교표: 기본 vs 개선

| 기능 | 기본 버전 | 개선 버전 |
|------|----------|----------|
| 필드 매핑 | 고정 (하드코딩) | 유연 (여러 필드명 시도) |
| API URL | 1개 고정 | 여러 URL 시도 가능 |
| 오류 감지 | CloudWatch Logs만 | 자동 알림 + Logs |
| 구조 변경 대응 | 수동 수정 | 자동 시도 + 알림 |
| 연속 실패 감지 | 없음 | 3회 연속 실패 시 알림 |
| 알림 방법 | 없음 | 이메일 (SNS) |

---

## 🎯 결론

### ❌ 완전 자동 수정은 불가능
- 구조 변경을 자동으로 "감지"는 가능
- 하지만 자동으로 "수정"은 불가능
- **사람의 개입 필요**

### ✅ 개선된 점
- 빠른 감지 및 알림 (이메일)
- 일부 변경사항 자동 대응 (필드명 변경 등)
- 연속 실패 방지 (다중 URL 시도)
- 모니터링 강화 (CloudWatch + SNS)

### 🚀 권장 사항
1. **개선 버전 사용** (lambda_crawler_with_monitoring.py)
2. **SNS 알림 설정** (이메일 수신)
3. **주 1회 CloudWatch Logs 점검**
4. **알림 수신 시 즉시 대응**

---

**예상 유지보수 시간**: 월 30분~1시간 (정상 운영 시)
**구조 변경 시 대응 시간**: 30분~2시간 (코드 수정 + 배포)
