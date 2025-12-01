# Lambda 완전 NOTAM API 배포 스크립트 (Windows PowerShell)
# 작성일: 2025-12-01
# 사용법: .\deploy_to_aws.ps1

$FunctionName = "notam-query-complete"
$RoleArn = "arn:aws:iam::496707410683:role/notam-lambda-role"
$ZipFile = "lambda_notam_query_complete.zip"
$Region = "ap-southeast-2"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Lambda 완전 NOTAM API 배포" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ====================================
# 1. 환경 및 파일 확인
# ====================================

Write-Host "[1/4] 환경 및 파일 확인..." -ForegroundColor Yellow

# AWS CLI 확인
if (!(Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] AWS CLI가 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host "설치: https://aws.amazon.com/cli/" -ForegroundColor Red
    exit 1
}

Write-Host "  - AWS CLI: OK" -ForegroundColor Green

# ZIP 파일 확인
if (!(Test-Path $ZipFile)) {
    Write-Host "[ERROR] ZIP 파일을 찾을 수 없습니다: $ZipFile" -ForegroundColor Red
    Write-Host "먼저 Lambda 패키지를 생성하세요." -ForegroundColor Yellow
    exit 1
}

$FileSize = [math]::Round((Get-Item $ZipFile).Length / 1KB, 1)
Write-Host "  - 배포 패키지: $ZipFile ($FileSize KB)" -ForegroundColor Green

# ====================================
# 2. Lambda 함수 생성/업데이트
# ====================================

Write-Host ""
Write-Host "[2/4] Lambda 함수 배포..." -ForegroundColor Yellow

$createOutput = aws lambda create-function `
    --function-name $FunctionName `
    --runtime python3.11 `
    --role $RoleArn `
    --handler lambda_function.lambda_handler `
    --zip-file fileb://$ZipFile `
    --timeout 300 `
    --memory-size 512 `
    --environment "Variables={BUCKET_NAME=notam-korea-data}" `
    --description "S3 154,986개 전체 NOTAM 조회 API" `
    --region $Region `
    2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  - Lambda 함수 생성 완료!" -ForegroundColor Green
} elseif ($createOutput -match "ResourceConflictException|already exists") {
    Write-Host "  - 함수가 이미 존재합니다. 업데이트 중..." -ForegroundColor Yellow

    # 코드 업데이트
    aws lambda update-function-code `
        --function-name $FunctionName `
        --zip-file fileb://$ZipFile `
        --region $Region | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  - 코드 업데이트 완료!" -ForegroundColor Green
    }

    # 설정 업데이트
    aws lambda update-function-configuration `
        --function-name $FunctionName `
        --timeout 300 `
        --memory-size 512 `
        --environment "Variables={BUCKET_NAME=notam-korea-data}" `
        --region $Region | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  - 설정 업데이트 완료!" -ForegroundColor Green
    }
} else {
    Write-Host "[ERROR] Lambda 함수 배포 실패:" -ForegroundColor Red
    Write-Host $createOutput -ForegroundColor Red
    Write-Host ""
    Write-Host "권한이 없는 경우, 수동으로 배포하세요:" -ForegroundColor Yellow
    Write-Host "https://ap-southeast-2.console.aws.amazon.com/lambda" -ForegroundColor White
    exit 1
}

# ====================================
# 3. API Gateway 권한 설정
# ====================================

Write-Host ""
Write-Host "[3/4] API Gateway 권한 설정..." -ForegroundColor Yellow

aws lambda add-permission `
    --function-name $FunctionName `
    --statement-id apigateway-notam-complete `
    --action lambda:InvokeFunction `
    --principal apigateway.amazonaws.com `
    --source-arn "arn:aws:execute-api:ap-southeast-2:496707410683:k9cp26l1ra/*" `
    --region $Region `
    2>&1 | Out-Null

if ($LASTEXITCODE -eq 0 -or $_ -match "ResourceConflictException") {
    Write-Host "  - API Gateway 권한 추가 완료!" -ForegroundColor Green
}

# ====================================
# 4. 배포 완료
# ====================================

Write-Host ""
Write-Host "[4/4] 배포 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Lambda 함수 정보:" -ForegroundColor Cyan
Write-Host "  - 함수 이름: $FunctionName" -ForegroundColor White
Write-Host "  - 리전: $Region" -ForegroundColor White
Write-Host "  - 메모리: 512 MB" -ForegroundColor White
Write-Host "  - 타임아웃: 300초" -ForegroundColor White
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "  1. API Gateway 엔드포인트 설정" -ForegroundColor White
Write-Host "     https://ap-southeast-2.console.aws.amazon.com/apigateway" -ForegroundColor White
Write-Host ""
Write-Host "  2. 가이드 문서 참조:" -ForegroundColor White
Write-Host "     DEPLOY_COMPLETE_NOTAM_API.md" -ForegroundColor White
Write-Host ""
Write-Host "  3. 테스트 명령:" -ForegroundColor White
Write-Host '     curl "https://k9cp26l1ra.execute-api.ap-southeast-2.amazonaws.com/prod/notams/stats"' -ForegroundColor White
Write-Host ""
