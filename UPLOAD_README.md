# S3 업로드 가이드

## 현재 상태

✅ **완료된 작업**
- 2023-2025년 NOTAM 데이터 수집: 72,800개
- JSON 파일 생성: `notam_data.json` (70.61 MB)
- S3 업로드 스크립트 준비 완료

❌ **필요한 작업**
- AWS 인증 정보 설정
- S3 업로드 실행

---

## 방법 1: AWS CLI 사용 (권장)

### 1단계: AWS CLI 설치 확인
```bash
aws --version
```

없으면 설치: https://aws.amazon.com/cli/

### 2단계: AWS 인증 정보 설정
```bash
aws configure
```

입력 항목:
- AWS Access Key ID: [AWS IAM에서 발급받은 키]
- AWS Secret Access Key: [AWS IAM에서 발급받은 시크릿]
- Default region name: `ap-northeast-2` (서울 리전)
- Default output format: `json`

### 3단계: S3 업로드 실행
```bash
py upload_to_both_buckets.py
```

---

## 방법 2: Python 스크립트로 인증 정보 설정

### 1단계: 인증 정보 설정 스크립트 실행
```bash
py setup_aws_credentials.py
```

### 2단계: S3 업로드 실행
```bash
py upload_to_both_buckets.py
```

---

## 방법 3: 환경 변수 사용 (임시)

### Windows (CMD)
```cmd
set AWS_ACCESS_KEY_ID=your_access_key_here
set AWS_SECRET_ACCESS_KEY=your_secret_key_here
py upload_to_both_buckets.py
```

### Windows (PowerShell)
```powershell
$env:AWS_ACCESS_KEY_ID="your_access_key_here"
$env:AWS_SECRET_ACCESS_KEY="your_secret_key_here"
py upload_to_both_buckets.py
```

---

## 업로드 대상 버킷

1. **notam-korea-data** (메인 데이터)
2. **notam-backup** (백업)

두 버킷 모두에 동일한 파일이 업로드됩니다.

---

## 파일 구조

```
notam_data.json              - 업로드할 데이터 (70.61 MB, 72,800개 NOTAM)
upload_to_both_buckets.py    - 양쪽 버킷 업로드 스크립트
setup_aws_credentials.py     - AWS 인증 정보 설정 도우미
upload_to_s3.py             - 단일 버킷 업로드 스크립트 (기존)
```

---

## 문제 해결

### "Unable to locate credentials" 오류
→ AWS 인증 정보가 설정되지 않음. 위 방법 중 하나로 설정 필요

### "NoSuchBucket" 오류
→ 버킷 이름 확인 또는 버킷이 다른 리전에 있는지 확인

### "Access Denied" 오류
→ IAM 사용자에게 S3 쓰기 권한이 없음. IAM 정책 확인 필요

---

## AWS IAM 권한 요구사항

최소 필요 권한:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::notam-korea-data/*",
        "arn:aws:s3:::notam-backup/*",
        "arn:aws:s3:::notam-korea-data",
        "arn:aws:s3:::notam-backup"
      ]
    }
  ]
}
```
