# AWS Lambda NOTAM 크롤러 배포 스크립트 (Windows PowerShell)
# 작성일: 2025-11-11
# 사용법: .\deploy_to_aws.ps1

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "AWS Lambda NOTAM 크롤러 배포" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ====================================
# 1. 환경 확인
# ====================================

Write-Host "[1/6] 환경 확인..." -ForegroundColor Yellow

# AWS CLI 확인
if (!(Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] AWS CLI가 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host "설치: https://aws.amazon.com/cli/" -ForegroundColor Red
    exit 1
}

Write-Host "  - AWS CLI: OK" -ForegroundColor Green

# Python 확인
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python이 설치되어 있지 않습니다." -ForegroundColor Red
    exit 1
}

Write-Host "  - Python: OK" -ForegroundColor Green

# ZIP 확인 (7-Zip 사용)
if (!(Get-Command 7z -ErrorAction SilentlyContinue)) {
    Write-Host "[WARN] 7-Zip이 없습니다. PowerShell Compress-Archive를 사용합니다." -ForegroundColor Yellow
    $USE_7ZIP = $false
} else {
    Write-Host "  - 7-Zip: OK" -ForegroundColor Green
    $USE_7ZIP = $true
}

# ====================================
# 2. 배포 폴더 생성
# ====================================

Write-Host ""
Write-Host "[2/6] 배포 폴더 생성..." -ForegroundColor Yellow

$DEPLOY_DIR = "deployment"

if (Test-Path $DEPLOY_DIR) {
    Remove-Item $DEPLOY_DIR -Recurse -Force
}

New-Item -ItemType Directory -Path $DEPLOY_DIR | Out-Null
New-Item -ItemType Directory -Path "$DEPLOY_DIR\crawler" | Out-Null
New-Item -ItemType Directory -Path "$DEPLOY_DIR\api" | Out-Null

Write-Host "  - deployment/ 폴더 생성됨" -ForegroundColor Green

# ====================================
# 3. Lambda 레이어 패키징
# ====================================

Write-Host ""
Write-Host "[3/6] Lambda 레이어 패키징..." -ForegroundColor Yellow

$LAYER_DIR = "$DEPLOY_DIR\layer\python"
New-Item -ItemType Directory -Path $LAYER_DIR -Force | Out-Null

Write-Host "  - Python 패키지 설치 중..."
pip install -r requirements.txt -t $LAYER_DIR --quiet

# ZIP 생성
Push-Location "$DEPLOY_DIR\layer"

if ($USE_7ZIP) {
    7z a -tzip lambda_layer.zip python\ | Out-Null
} else {
    Compress-Archive -Path python -DestinationPath lambda_layer.zip -Force
}

Pop-Location

$layerSize = [math]::Round((Get-Item "$DEPLOY_DIR\layer\lambda_layer.zip").Length / 1MB, 2)
Write-Host ("  - lambda_layer.zip 생성됨 (" + $layerSize + " MB)") -ForegroundColor Green

# ====================================
# 4. Lambda 크롤러 패키징
# ====================================

Write-Host ""
Write-Host "[4/6] Lambda 크롤러 패키징..." -ForegroundColor Yellow

# 크롤러 파일 복사
Copy-Item lambda_crawler.py "$DEPLOY_DIR\crawler\"

# ZIP 생성
Push-Location "$DEPLOY_DIR\crawler"

if ($USE_7ZIP) {
    7z a -tzip lambda_crawler.zip *.py | Out-Null
} else {
    Compress-Archive -Path *.py -DestinationPath lambda_crawler.zip -Force
}

Pop-Location

$crawlerSize = [math]::Round((Get-Item "$DEPLOY_DIR\crawler\lambda_crawler.zip").Length / 1KB, 2)
Write-Host ("  - lambda_crawler.zip 생성됨 (" + $crawlerSize + " KB)") -ForegroundColor Green

# ====================================
# 5. Lambda API 핸들러 패키징
# ====================================

Write-Host ""
Write-Host "[5/6] Lambda API 핸들러 패키징..." -ForegroundColor Yellow

# API 파일 복사
Copy-Item lambda_api_handlers.py "$DEPLOY_DIR\api\"

# ZIP 생성
Push-Location "$DEPLOY_DIR\api"

if ($USE_7ZIP) {
    7z a -tzip lambda_api.zip *.py | Out-Null
} else {
    Compress-Archive -Path *.py -DestinationPath lambda_api.zip -Force
}

Pop-Location

$apiSize = [math]::Round((Get-Item "$DEPLOY_DIR\api\lambda_api.zip").Length / 1KB, 2)
Write-Host ("  - lambda_api.zip 생성됨 (" + $apiSize + " KB)") -ForegroundColor Green

# ====================================
# 6. 배포 완료
# ====================================

Write-Host ""
Write-Host "[6/6] 배포 준비 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "생성된 파일:" -ForegroundColor Cyan
Write-Host "  - deployment/layer/lambda_layer.zip" -ForegroundColor White
Write-Host "  - deployment/crawler/lambda_crawler.zip" -ForegroundColor White
Write-Host "  - deployment/api/lambda_api.zip" -ForegroundColor White
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "  1. AWS 콘솔 접속: https://console.aws.amazon.com" -ForegroundColor White
Write-Host "  2. Lambda -> 레이어 -> 레이어 생성" -ForegroundColor White
Write-Host "     - lambda_layer.zip 업로드" -ForegroundColor White
Write-Host "  3. Lambda -> 함수 -> 함수 생성" -ForegroundColor White
Write-Host "     - lambda_crawler.zip 업로드" -ForegroundColor White
Write-Host "     - lambda_api.zip 업로드" -ForegroundColor White
Write-Host ""
Write-Host "자세한 가이드: AWS_DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
