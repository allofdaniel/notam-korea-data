# NOTAM Korea 배포 및 운영 가이드

## 📋 목차
1. [시스템 아키텍처](#시스템-아키텍처)
2. [백엔드 배포 (AWS EC2)](#백엔드-배포)
3. [프론트엔드 실행](#프론트엔드-실행)
4. [데이터베이스 관리](#데이터베이스-관리)
5. [모니터링 및 유지보수](#모니터링-및-유지보수)

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────┐
│                 사용자                            │
│         (Web / Android / iOS)                   │
└────────────┬────────────────────────────────────┘
             │
             │ HTTP/HTTPS
             ▼
┌─────────────────────────────────────────────────┐
│           React Native App (Expo)               │
│  - 지도 시각화 (Leaflet/react-native-maps)       │
│  - NOTAM 목록/검색/필터                          │
│  - 실시간 데이터 업데이트                         │
└────────────┬────────────────────────────────────┘
             │
             │ REST API
             ▼
┌─────────────────────────────────────────────────┐
│      AWS EC2 (Ubuntu 24.04 LTS)                 │
│  IP: 3.27.240.67                                │
│                                                 │
│  ┌──────────────────────────────────────┐      │
│  │ Flask API Server (Port 8000)         │      │
│  │  - /api/notams                       │      │
│  │  - /api/active                       │      │
│  │  - /api/recent                       │      │
│  │  - /api/stats                        │      │
│  └──────────────────────────────────────┘      │
│                                                 │
│  ┌──────────────────────────────────────┐      │
│  │ SQLite Database                      │      │
│  │  - notam_realtime.db (3MB)          │      │
│  │  - 5,655개 NOTAM 저장                │      │
│  │  - 7개 성능 인덱스                    │      │
│  └──────────────────────────────────────┘      │
│                                                 │
│  ┌──────────────────────────────────────┐      │
│  │ Cron Jobs                            │      │
│  │  - NOTAM 크롤러 (5분마다)             │      │
│  │  - DynamoDB 동기화 (1분마다)          │      │
│  └──────────────────────────────────────┘      │
└─────────────────────────────────────────────────┘
             │
             │ Web Scraping
             ▼
┌─────────────────────────────────────────────────┐
│        AIM Korea 포털                            │
│   https://aim.koca.go.kr                        │
│   - 국내/국제 NOTAM 제공                         │
└─────────────────────────────────────────────────┘
```

---

## 백엔드 배포

### EC2 서버 접속
```bash
ssh -i notam-crawler-key.pem ubuntu@3.27.240.67
```

### 현재 실행 중인 서비스 확인
```bash
# API 서버 확인
ps aux | grep ec2_api_server

# 크롤러 확인
crontab -l

# 데이터베이스 확인
ls -lh *.db
```

### API 서버 재시작
```bash
# 기존 프로세스 종료
pkill -f ec2_api_server

# 새로 시작
nohup python3 ec2_api_server.py > api_server.log 2>&1 &

# 로그 확인
tail -f api_server.log
```

### 크롤러 수동 실행
```bash
# 즉시 실행
python3 notam_crawler.py

# 로그 확인
tail -f crawler.log
```

### 데이터베이스 백업
```bash
# 백업 생성
sqlite3 notam_realtime.db ".backup notam_backup_$(date +%Y%m%d_%H%M%S).db"

# 백업 파일 확인
ls -lh notam_backup_*.db

# S3 업로드 (선택사항)
aws s3 cp notam_backup_*.db s3://your-bucket-name/backups/
```

---

## 프론트엔드 실행

### 개발 환경
```bash
cd C:/Users/allof/Desktop/code/notam-app

# 웹 브라우저에서 실행
npx expo start --web

# Android 에뮬레이터
npx expo start --android

# iOS 시뮬레이터 (Mac only)
npx expo start --ios
```

### 프로덕션 빌드
```bash
# 웹 빌드
npx expo export:web

# Android APK
eas build --platform android

# iOS IPA
eas build --platform ios
```

### 환경 변수 설정
`.env` 파일 생성:
```env
API_BASE_URL=http://3.27.240.67:8000
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
```

---

## 데이터베이스 관리

### 현재 데이터베이스 구조
```sql
-- notam_realtime.db
CREATE TABLE notams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notam_number TEXT UNIQUE,  -- 중복 방지
    a_location TEXT,           -- 공항 ICAO
    b_start_time TEXT,         -- 발효 시작
    c_end_time TEXT,           -- 발효 종료
    q_code TEXT,               -- NOTAM 타입
    e_text TEXT,               -- NOTAM 전문
    full_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 인덱스 목록
```sql
-- 성능 최적화 인덱스
CREATE INDEX idx_a_location ON notams(a_location);
CREATE INDEX idx_b_start_time ON notams(b_start_time);
CREATE INDEX idx_c_end_time ON notams(c_end_time);
CREATE INDEX idx_q_code ON notams(q_code);
CREATE INDEX idx_location_start ON notams(a_location, b_start_time DESC);
CREATE INDEX idx_qcode_start ON notams(q_code, b_start_time DESC);
```

### 유용한 SQL 쿼리
```sql
-- 전체 통계
SELECT
    COUNT(*) as total,
    COUNT(DISTINCT a_location) as airports,
    MIN(b_start_time) as oldest,
    MAX(b_start_time) as newest
FROM notams;

-- 공항별 NOTAM 개수
SELECT a_location, COUNT(*) as count
FROM notams
GROUP BY a_location
ORDER BY count DESC;

-- 활성 NOTAM (발효 중)
SELECT COUNT(*) FROM notams
WHERE datetime(b_start_time) <= datetime('now')
  AND (c_end_time = 'PERM' OR datetime(c_end_time) > datetime('now'));

-- 타입별 분류
SELECT
    SUBSTR(q_code, 1, 2) as category,
    COUNT(*) as count
FROM notams
WHERE q_code IS NOT NULL
GROUP BY category
ORDER BY count DESC;

-- 최근 24시간 추가된 NOTAM
SELECT * FROM notams
WHERE created_at >= datetime('now', '-1 day')
ORDER BY created_at DESC;
```

### 데이터베이스 최적화
```bash
# EC2에서 실행
sqlite3 notam_realtime.db << EOF
-- 통계 업데이트
ANALYZE;

-- 불필요한 공간 정리
VACUUM;

-- 무결성 검사
PRAGMA integrity_check;
EOF
```

---

## 모니터링 및 유지보수

### API 서버 헬스체크
```bash
# 로컬에서 실행
curl http://3.27.240.67:8000/api/stats

# 예상 응답:
# {
#   "total": 5655,
#   "active": 4102,
#   "airports": 18,
#   "last_update": "2025-11-15T12:45:00"
# }
```

### 로그 모니터링
```bash
# API 서버 로그 (실시간)
ssh ubuntu@3.27.240.67 "tail -f /home/ubuntu/api_server.log"

# 크롤러 로그
ssh ubuntu@3.27.240.67 "tail -f /home/ubuntu/crawler.log"

# 시스템 리소스
ssh ubuntu@3.27.240.67 "htop"
```

### 디스크 공간 확인
```bash
ssh ubuntu@3.27.240.67 "df -h"
ssh ubuntu@3.27.240.67 "du -sh /home/ubuntu/*.db"
```

### Cron 작업 확인
```bash
ssh ubuntu@3.27.240.67 "crontab -l"

# 현재 설정:
# */5 * * * * cd /home/ubuntu && python3 notam_crawler.py >> crawler.log 2>&1
# * * * * * cd /home/ubuntu && python3 sync_to_dynamodb.py >> sync.log 2>&1
```

### 문제 해결

**1. API 서버 응답 없음**
```bash
# 프로세스 확인
ps aux | grep ec2_api_server

# 포트 확인
netstat -tulpn | grep 8000

# 재시작
pkill -f ec2_api_server && python3 ec2_api_server.py &
```

**2. 크롤러 작동 안 함**
```bash
# 수동 실행 테스트
python3 notam_crawler.py

# 로그 확인
tail -100 crawler.log

# Cron 재설정
crontab -e
```

**3. 데이터베이스 손상**
```bash
# 무결성 검사
sqlite3 notam_realtime.db "PRAGMA integrity_check;"

# 백업에서 복원
cp notam_backup_YYYYMMDD_HHMMSS.db notam_realtime.db
```

---

## 성능 최적화 팁

### 1. API 응답 속도
- ✅ 인덱스 적용 완료 (7개)
- ✅ LIMIT 제거 (전체 데이터 반환)
- 🔄 Redis 캐싱 고려 (미래)

### 2. 프론트엔드 렌더링
- ✅ 가상화 리스트 (FlatList)
- ✅ 지도 영역 필터링 (화면 내만 렌더)
- 🔄 Web Worker 활용 (좌표 파싱)

### 3. 데이터베이스 크기
- 현재: 3MB (5,655개 NOTAM)
- 1년 예상: ~50MB
- 정리 전략: 6개월 이상 종료된 NOTAM 아카이브

---

## 보안 체크리스트

- [ ] API 키 환경 변수화
- [ ] HTTPS 적용 (Let's Encrypt)
- [ ] Rate Limiting 설정
- [ ] CORS 정책 강화
- [ ] 데이터베이스 암호화
- [ ] SSH 키 관리 (정기 교체)

---

## 연락처 및 지원

- **개발자**: allof
- **EC2 IP**: 3.27.240.67
- **프로젝트**: C:\Users\allof\Desktop\code
- **문서 버전**: 1.0 (2025-11-15)

---

**마지막 업데이트**: 2025-11-15
**상태**: ✅ 프로덕션 준비 완료
