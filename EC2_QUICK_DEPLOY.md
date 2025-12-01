# EC2에 완전 NOTAM API 배포 (2분)

## 명령어 한 줄로 완료

PowerShell이나 CMD에서 실행:

```bash
ssh -i notam-crawler-key.pem ubuntu@3.27.240.67 "cd /home/ubuntu && git clone https://github.com/allofdaniel/notam-korea-data.git temp_code 2>/dev/null || (cd temp_code && git pull) && cp temp_code/ec2_complete_notam_api.py . && pkill -f ec2_complete_notam_api && nohup python3 ec2_complete_notam_api.py > complete_api.log 2>&1 & sleep 2 && tail -20 complete_api.log"
```

## 또는 단계별로:

### 1. EC2 접속
```bash
ssh -i notam-crawler-key.pem ubuntu@3.27.240.67
```

### 2. 코드 다운로드
```bash
cd /home/ubuntu
git clone https://github.com/allofdaniel/notam-korea-data.git temp_code
# 또는 이미 있으면
cd temp_code && git pull && cd ..
```

### 3. API 파일 복사
```bash
cp temp_code/ec2_complete_notam_api.py .
```

### 4. 기존 서버 중지 (있으면)
```bash
pkill -f ec2_complete_notam_api
```

### 5. 새 API 서버 시작
```bash
nohup python3 ec2_complete_notam_api.py > complete_api.log 2>&1 &
```

### 6. 로그 확인
```bash
tail -f complete_api.log
```

예상 출력:
```
============================================================
EC2 완전 NOTAM API 서버
============================================================
[LOAD] S3에서 전체 NOTAM 로드 중...
[OK] 154986개 NOTAM 로드 완료

엔드포인트:
  GET /notams/stats
  GET /notams/active
  GET /notams/expired
  GET /notams/trigger
  GET /notams/complete
  GET /notams/date/<date>
  GET /health

서버 시작 중...
 * Running on http://0.0.0.0:8000/
```

## 테스트

```bash
# 로컬에서
curl "http://3.27.240.67:8000/notams/stats"
```

## 앱 연결

`notam-app/src/config/constants.js` 변경 필요 없음!
기존 EC2 API 엔드포인트에 자동으로 연결됩니다.

새 엔드포인트만 추가하면 됩니다.
