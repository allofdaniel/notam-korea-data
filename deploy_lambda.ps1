# Lambda NOTAM API 배포 스크립트
# EC2 → Lambda 마이그레이션

Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 58) -ForegroundColor Cyan
Write-Host "Lambda NOTAM API 배포" -ForegroundColor Yellow
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 58) -ForegroundColor Cyan

# 설정
$FUNCTION_NAME = "notam-api-lambda"
$ROLE_NAME = "lambda-notam-api-role"
$REGION = "ap-southeast-2"  # Sydney (EC2와 같은 리전)

# 1. Lambda 실행 역할 생성 (없으면)
Write-Host "`n[1/6] Lambda 실행 역할 확인..." -ForegroundColor Cyan

$roleExists = aws iam get-role --role-name $ROLE_NAME 2>$null
if (-not $roleExists) {
    Write-Host "  → 역할 생성 중..." -ForegroundColor Yellow

    # Trust Policy 생성
    $trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@

    Set-Content -Path "trust-policy.json" -Value $trustPolicy

    aws iam create-role `
        --role-name $ROLE_NAME `
        --assume-role-policy-document file://trust-policy.json `
        --description "Lambda NOTAM API execution role"

    # 필수 정책 연결
    aws iam attach-role-policy `
        --role-name $ROLE_NAME `
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

    aws iam attach-role-policy `
        --role-name $ROLE_NAME `
        --policy-arn "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"

    Remove-Item "trust-policy.json"

    Write-Host "  ✓ 역할 생성 완료" -ForegroundColor Green
    Start-Sleep -Seconds 10  # IAM 전파 대기
} else {
    Write-Host "  ✓ 역할 이미 존재" -ForegroundColor Green
}

# 2. 배포 패키지 생성
Write-Host "`n[2/6] 배포 패키지 생성..." -ForegroundColor Cyan

if (Test-Path "lambda_deploy.zip") {
    Remove-Item "lambda_deploy.zip"
}

Compress-Archive -Path "lambda_notam_api.py" -DestinationPath "lambda_deploy.zip"
Write-Host "  ✓ lambda_deploy.zip 생성 완료" -ForegroundColor Green

# 3. Lambda 함수 생성/업데이트
Write-Host "`n[3/6] Lambda 함수 배포..." -ForegroundColor Cyan

$functionExists = aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>$null
$roleArn = aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text

if (-not $functionExists) {
    Write-Host "  → 새 Lambda 함수 생성..." -ForegroundColor Yellow

    aws lambda create-function `
        --function-name $FUNCTION_NAME `
        --runtime python3.12 `
        --role $roleArn `
        --handler lambda_notam_api.lambda_handler `
        --zip-file fileb://lambda_deploy.zip `
        --timeout 30 `
        --memory-size 512 `
        --region $REGION `
        --description "NOTAM API (S3 기반)"

    Write-Host "  ✓ Lambda 함수 생성 완료" -ForegroundColor Green
} else {
    Write-Host "  → 기존 Lambda 함수 업데이트..." -ForegroundColor Yellow

    aws lambda update-function-code `
        --function-name $FUNCTION_NAME `
        --zip-file fileb://lambda_deploy.zip `
        --region $REGION

    Write-Host "  ✓ Lambda 함수 업데이트 완료" -ForegroundColor Green
}

# 4. Function URL 생성
Write-Host "`n[4/6] Function URL 설정..." -ForegroundColor Cyan

$urlConfig = aws lambda get-function-url-config `
    --function-name $FUNCTION_NAME `
    --region $REGION 2>$null

if (-not $urlConfig) {
    Write-Host "  → Function URL 생성..." -ForegroundColor Yellow

    aws lambda create-function-url-config `
        --function-name $FUNCTION_NAME `
        --auth-type NONE `
        --cors "AllowOrigins=*,AllowMethods=GET,AllowHeaders=*" `
        --region $REGION

    # 공개 접근 권한 부여
    aws lambda add-permission `
        --function-name $FUNCTION_NAME `
        --statement-id FunctionURLAllowPublicAccess `
        --action lambda:InvokeFunctionUrl `
        --principal "*" `
        --function-url-auth-type NONE `
        --region $REGION

    Write-Host "  ✓ Function URL 생성 완료" -ForegroundColor Green
} else {
    Write-Host "  ✓ Function URL 이미 존재" -ForegroundColor Green
}

# 5. Function URL 가져오기
Write-Host "`n[5/6] Function URL 확인..." -ForegroundColor Cyan

$functionUrl = aws lambda get-function-url-config `
    --function-name $FUNCTION_NAME `
    --region $REGION `
    --query 'FunctionUrl' `
    --output text

Write-Host "`n✅ Lambda 배포 완료!" -ForegroundColor Green
Write-Host "`nFunction URL:" -ForegroundColor Cyan
Write-Host "  $functionUrl" -ForegroundColor Yellow

# 6. 테스트
Write-Host "`n[6/6] API 테스트..." -ForegroundColor Cyan

Write-Host "  → Health check..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "${functionUrl}health" -Method Get
    Write-Host "  ✓ API 정상 작동" -ForegroundColor Green
    Write-Host "  Total NOTAMs: $($response.total_notams)" -ForegroundColor White
} catch {
    Write-Host "  ⚠ API 테스트 실패: $_" -ForegroundColor Red
}

Write-Host "`n" -NoNewline
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 58) -ForegroundColor Cyan
Write-Host "다음 단계" -ForegroundColor Yellow
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 58) -ForegroundColor Cyan
Write-Host "`n1. Vercel proxy 업데이트:" -ForegroundColor Cyan
Write-Host "   notam-web/api/proxy.js 파일에서" -ForegroundColor White
Write-Host "   EC2_API_URL을" -ForegroundColor White
Write-Host "   '$functionUrl'" -ForegroundColor Yellow
Write-Host "   로 변경하세요`n" -ForegroundColor White

Write-Host "2. 비용 절감:" -ForegroundColor Cyan
Write-Host "   Lambda 배포 후 EC2 인스턴스를 중지하세요" -ForegroundColor White
Write-Host "   월 $8.91 절감 가능`n" -ForegroundColor Green

Write-Host "3. 크롤러는 계속 S3에 저장 (EC2 또는 EventBridge)" -ForegroundColor Cyan

# 정리
Remove-Item "lambda_deploy.zip" -ErrorAction SilentlyContinue
