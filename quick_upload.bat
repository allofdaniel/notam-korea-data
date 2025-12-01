@echo off
REM NOTAM 데이터 S3 빠른 업로드 스크립트
REM
REM 사용법:
REM   1. 이 파일을 편집하여 AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY 입력
REM   2. quick_upload.bat 실행

echo ================================================================================
echo NOTAM 데이터 S3 업로드
echo ================================================================================
echo.

REM AWS 인증 정보 설정 (여기에 실제 키 입력)
set AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_HERE
set AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY_HERE
set AWS_DEFAULT_REGION=ap-northeast-2

REM 인증 정보 확인
if "%AWS_ACCESS_KEY_ID%"=="YOUR_ACCESS_KEY_HERE" (
    echo [ERROR] AWS_ACCESS_KEY_ID를 설정하세요!
    echo.
    echo 이 파일을 텍스트 에디터로 열어서:
    echo   set AWS_ACCESS_KEY_ID=실제_액세스_키
    echo   set AWS_SECRET_ACCESS_KEY=실제_시크릿_키
    echo 로 수정하세요.
    echo.
    pause
    exit /b 1
)

echo [INFO] AWS 인증 정보 확인됨
echo [INFO] 업로드 시작...
echo.

REM Python 스크립트 실행
py upload_to_both_buckets.py

if %errorlevel% equ 0 (
    echo.
    echo ================================================================================
    echo [완료] S3 업로드 성공!
    echo ================================================================================
) else (
    echo.
    echo ================================================================================
    echo [실패] S3 업로드 실패
    echo ================================================================================
)

echo.
pause
