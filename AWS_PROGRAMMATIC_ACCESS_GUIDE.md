# AWS 프로그래밍 방식 제어 설정 가이드

## 🎯 목표

Claude Code가 AWS Console 없이 직접 AWS를 제어할 수 있도록 설정

## 📋 필요한 것

1. AWS Access Key ID
2. AWS Secret Access Key
3. 적절한 IAM 권한

## 🚀 빠른 설정 (3분)

### 1단계: AWS Access Key 생성

AWS Console에서:

1. **IAM 서비스** 이동
2. **Users** → 본인 계정 (`daniel`) 클릭
3. **Security credentials** 탭
4. **Create access key** 클릭
5. **Use case**: Command Line Interface (CLI)
6. 체크박스 ☑️ "I understand..."
7. **Next** → **Create access key**
8. **중요**: Access Key ID와 Secret Access Key 복사 (다시 볼 수 없음!)

### 2단계: 로컬에 자격 증명 설정

아래 PowerShell 스크립트 실행:

```powershell
py setup_aws_credentials.py
```

스크립트가 물어보면:
- AWS Access Key ID: (1단계에서 복사한 것)
- AWS Secret Access Key: (1단계에서 복사한 것)
- Region: ap-southeast-2 (현재 사용 중인 리전)

### 3단계: 확인

```powershell
py -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

성공하면:
```json
{
  "UserId": "AIDASAMPLEUSERID",
  "Account": "496707410683",
  "Arn": "arn:aws:iam::496707410683:user/daniel"
}
```

## ✅ 완료!

이제 Claude Code가 직접:
- Lambda 함수 생성/업데이트
- API Gateway 설정
- S3 업로드/다운로드
- EventBridge 스케줄 설정
- IAM 역할 관리

모든 작업을 대화 중에 자동으로 수행할 수 있습니다!

## 🔐 보안 권장사항

### 1. 최소 권한 원칙
사용자에게 필요한 권한만 부여:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:*",
        "apigateway:*",
        "s3:*",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole",
        "events:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. Access Key 보호
- ❌ Git에 커밋 금지
- ❌ 코드에 하드코딩 금지
- ✅ `.aws/credentials` 파일에만 저장
- ✅ 정기적으로 로테이션 (90일마다)

### 3. MFA 설정 (선택사항)
더 강력한 보안을 위해 MFA 활성화

## 📂 자격 증명 저장 위치

Windows:
```
C:\Users\allof\.aws\credentials
C:\Users\allof\.aws\config
```

내용 (자동 생성됨):
```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
region = ap-southeast-2
```

## 🛠️ 문제 해결

### Access Key 생성 시 "You cannot create more than 2 access keys"
- 기존 Access Key 삭제 후 새로 생성
- 또는 기존 키 사용

### "Unable to locate credentials"
```powershell
# 자격 증명 확인
cat ~\.aws\credentials

# 없으면 다시 설정
py setup_aws_credentials.py
```

### "Access Denied" 오류
IAM 사용자에 필요한 권한 추가:
- AWSLambda_FullAccess
- AmazonAPIGatewayAdministrator
- AmazonS3FullAccess
- IAMFullAccess (또는 특정 권한만)

## 🎓 이제 가능한 작업

### 1. Lambda 자동 배포
```powershell
py deploy_lambda.py
```
→ 콘솔 조작 없이 자동 배포!

### 2. API Gateway 설정
대화 중에:
"API Gateway에 /notams/search 엔드포인트 추가해줘"
→ 자동으로 생성!

### 3. S3 데이터 관리
"S3에 있는 오늘 NOTAM 데이터 보여줘"
→ 자동으로 조회!

### 4. 실시간 모니터링
"Lambda 함수 실행 로그 보여줘"
→ CloudWatch Logs 자동 조회!

## 🔄 Access Key 로테이션 (90일마다)

1. 새 Access Key 생성
2. `py setup_aws_credentials.py` 실행
3. 새 키로 테스트
4. 이전 키 비활성화
5. 7일 후 이전 키 삭제

## 📞 다음 단계

자격 증명 설정 후:

```powershell
# 1. Lambda 자동 배포
py deploy_lambda.py

# 2. 테스트
py -c "import boto3; lambda_client = boto3.client('lambda'); print(lambda_client.list_functions())"
```

## 💡 팁

### 여러 AWS 계정 사용 시
```ini
[default]
aws_access_key_id = KEY1
aws_secret_access_key = SECRET1

[production]
aws_access_key_id = KEY2
aws_secret_access_key = SECRET2
```

사용:
```python
session = boto3.Session(profile_name='production')
```

### 임시 자격 증명 (더 안전)
AWS STS로 임시 자격 증명 사용 가능 (1-12시간 유효)

## ⚠️ 주의사항

1. **절대 공유 금지**: Access Key는 패스워드와 같음
2. **Git 커밋 금지**: `.gitignore`에 `.aws/` 추가
3. **정기 검토**: 사용하지 않는 키는 삭제
4. **알림 설정**: IAM Access Analyzer로 이상 활동 감지
