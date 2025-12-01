# 🚀 Claude Code가 AWS를 직접 제어하도록 설정하기

## 현재 상황

지금은 AWS 작업을 할 때마다 사용자가 직접 AWS Console에서 수동으로 작업해야 합니다.

## 목표

Claude Code가 대화 중에 자동으로:
- Lambda 함수 생성/업데이트
- API Gateway 설정
- S3 업로드/다운로드
- EventBridge 스케줄 설정
- CloudWatch 로그 조회

모든 작업을 **자동으로** 수행하도록 설정합니다.

## 🎯 3단계로 완료 (5분)

### 1단계: AWS Access Key 생성 (2분)

1. AWS Console 접속: https://console.aws.amazon.com
2. 우측 상단 **계정명** 클릭 → **Security credentials**
3. **Access keys** 섹션 → **Create access key**
4. Use case: **Command Line Interface (CLI)** 선택
5. 체크박스 ☑️ "I understand the above recommendation and want to proceed to create an access key"
6. **Next** → **Create access key**
7. **중요**: 아래 두 값을 복사하세요 (다시 볼 수 없습니다!)
   - **Access key ID**: `AKIA...` (복사)
   - **Secret access key**: `wJalr...` (복사)

### 2단계: 로컬에 자격 증명 저장 (1분)

PowerShell이나 CMD에서:

```powershell
py setup_aws_credentials.py
```

물어보면 1단계에서 복사한 값 입력:
```
AWS Access Key ID: AKIA...  (붙여넣기)
AWS Secret Access Key: wJalr...  (붙여넣기)
Region (Enter = ap-northeast-2): ap-southeast-2  (현재 사용 중인 리전)
```

### 3단계: 확인 (1분)

```powershell
py -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

성공하면:
```json
{
  'UserId': 'AIDASAMPLEUSERID',
  'Account': '496707410683',
  'Arn': 'arn:aws:iam::496707410683:user/daniel'
}
```

## ✅ 완료!

이제 Claude Code와 대화할 때:

### Before (지금):
```
사용자: "Lambda 함수 생성해줘"
Claude: "AWS Console에서 다음 단계를 따라주세요..."
사용자: (직접 AWS Console 조작)
```

### After (설정 후):
```
사용자: "Lambda 함수 생성해줘"
Claude: (자동으로 Lambda 함수 생성)
Claude: "[OK] notam-realtime-crawler 함수 생성 완료!"
```

## 💡 이제 가능한 것들

### 1. Lambda 자동 배포
```
사용자: Lambda 함수 배포해줘
→ Claude: 자동으로 배포 완료!
```

### 2. S3 데이터 조회/업로드
```
사용자: S3에 있는 오늘 NOTAM 데이터 보여줘
→ Claude: 자동으로 데이터 조회 후 보여줌
```

### 3. API Gateway 설정
```
사용자: API Gateway에 /notams/search 엔드포인트 추가해줘
→ Claude: 자동으로 엔드포인트 생성
```

### 4. CloudWatch 로그 확인
```
사용자: Lambda 실행 로그 보여줘
→ Claude: 최근 로그 자동 조회
```

### 5. 실시간 모니터링
```
사용자: 지금까지 수집된 NOTAM 개수는?
→ Claude: S3에서 자동으로 계산
```

## 🔐 보안

- Access Key는 `C:\Users\allof\.aws\credentials`에만 저장됨
- Git에 커밋되지 않음 (`.gitignore`에 추가됨)
- 로컬 컴퓨터에만 저장됨
- 언제든지 AWS Console에서 비활성화/삭제 가능

## ⚠️ 중요

1. **Access Key는 패스워드입니다** - 절대 공유 금지!
2. **90일마다 로테이션 권장** - 보안 강화
3. **사용하지 않으면 비활성화** - IAM > Users > Security credentials에서

## 🎓 다음 단계

자격 증명 설정 후 바로 사용 가능:

```powershell
# Lambda 자동 배포
py deploy_lambda.py

# 또는 Claude Code와 대화:
# "Lambda 함수 배포해줘"
# "S3에 데이터 업로드해줘"
# "API Gateway 설정 확인해줘"
```

## 📚 상세 가이드

- **AWS_PROGRAMMATIC_ACCESS_GUIDE.md** - 상세 설정 가이드
- **LAMBDA_MANUAL_SETUP.md** - 수동 Lambda 설정 (필요시)
- **FINAL_SUMMARY.md** - 전체 프로젝트 요약

## 🆘 문제 해결

### "No module named 'boto3'"
```powershell
pip install boto3
```

### "Unable to locate credentials"
```powershell
# 자격 증명 다시 설정
py setup_aws_credentials.py
```

### "Access Denied"
AWS Console에서 IAM 사용자에 권한 추가:
- AWSLambda_FullAccess
- AmazonAPIGatewayAdministrator
- AmazonS3FullAccess
