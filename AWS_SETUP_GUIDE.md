# AWS S3 업로드 설정 가이드

## 📋 필요한 정보

S3에 업로드하려면 다음 3가지 정보가 필요합니다:

1. **AWS Access Key ID** (예: AKIAIOSFODNN7EXAMPLE)
2. **AWS Secret Access Key** (예: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY)
3. **Region** (선택사항, 기본값: ap-northeast-2)

## 🔑 AWS Access Key 발급 방법

### 1단계: AWS Console 로그인
https://console.aws.amazon.com 접속

### 2단계: IAM으로 이동
- 검색창에 "IAM" 입력
- IAM 서비스 선택

### 3단계: Access Key 생성
1. 좌측 메뉴에서 **Users** 클릭
2. 본인 사용자명 클릭 (또는 새 사용자 생성)
3. **Security credentials** 탭 클릭
4. **Access keys** 섹션에서 **Create access key** 클릭
5. Use case: **Other** 선택
6. **Access Key ID**와 **Secret Access Key** 복사 (한 번만 표시됨!)

### 4단계: S3 권한 확인
IAM 사용자에게 S3 권한이 있어야 합니다:
1. IAM > Users > 본인 사용자
2. **Permissions** 탭
3. **Add permissions** 클릭
4. **Attach policies directly** 선택
5. **AmazonS3FullAccess** 검색 후 체크
6. **Next** > **Add permissions** 클릭

## 💻 자격 증명 설정 방법

### 방법 1: 자동 설정 스크립트 (권장)

```bash
py setup_aws_credentials.py
```

입력 프롬프트에 따라 정보 입력:
```
AWS Access Key ID: [여기에 입력]
AWS Secret Access Key: [여기에 입력]
AWS Region (Enter = ap-northeast-2): [Enter 또는 리전 입력]
```

### 방법 2: 수동 설정

#### Windows:
```bash
mkdir %USERPROFILE%\.aws
notepad %USERPROFILE%\.aws\credentials
```

`credentials` 파일 내용:
```
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

`config` 파일 생성:
```bash
notepad %USERPROFILE%\.aws\config
```

`config` 파일 내용:
```
[default]
region = ap-northeast-2
```

#### macOS/Linux:
```bash
mkdir -p ~/.aws
nano ~/.aws/credentials
```

`credentials` 파일 내용:
```
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

`config` 파일:
```bash
nano ~/.aws/config
```

`config` 파일 내용:
```
[default]
region = ap-northeast-2
```

## 🪣 S3 버킷 생성

업로드하기 전에 S3 버킷이 필요합니다:

### 1. AWS Console에서 S3 서비스 열기
https://s3.console.aws.amazon.com/

### 2. 버킷 생성
1. **Create bucket** 클릭
2. **Bucket name**: `notam-korea-data` 입력
3. **Region**: `ap-northeast-2` (서울) 선택
4. 나머지 설정은 기본값
5. **Create bucket** 클릭

### 3. 백업 버킷 생성 (선택사항)
위 과정 반복해서 `notam-backup` 버킷 생성

## ✅ 설정 확인

```bash
py setup_aws_credentials.py
```

성공 시 출력:
```
[OK] AWS 연결 성공!

사용 가능한 버킷:
  - notam-korea-data
  - notam-backup
```

## 🚀 S3 업로드 실행

설정 완료 후:
```bash
py upload_complete_to_s3.py
```

## ⚠️ 문제 해결

### boto3 설치 안됨
```bash
pip install boto3
```

### 권한 오류
```
An error occurred (AccessDenied) when calling the ListBuckets operation
```
→ IAM 사용자에게 S3 권한 추가 필요 (위 4단계 참조)

### 자격 증명 오류
```
Unable to locate credentials
```
→ `~/.aws/credentials` 파일 확인
→ Access Key ID/Secret Key 재입력

### 버킷 없음
```
The specified bucket does not exist
```
→ S3 Console에서 버킷 생성 필요

## 📞 추가 도움

- AWS 공식 문서: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
- boto3 문서: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
