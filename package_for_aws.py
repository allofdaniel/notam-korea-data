"""
AWS Lambda 배포 패키지 생성 스크립트
"""
import os
import shutil
import zipfile
import subprocess

print("=" * 50)
print("AWS Lambda NOTAM 크롤러 배포 패키지 생성")
print("=" * 50)
print()

DEPLOY_DIR = "deployment"

# 1. 배포 폴더 생성
print("[1/6] 배포 폴더 생성...")
if os.path.exists(DEPLOY_DIR):
    try:
        shutil.rmtree(DEPLOY_DIR)
    except PermissionError:
        print("  ! 기존 폴더 삭제 실패, 덮어쓰기 진행...")

os.makedirs(f"{DEPLOY_DIR}/layer/python", exist_ok=True)
os.makedirs(f"{DEPLOY_DIR}/crawler", exist_ok=True)
os.makedirs(f"{DEPLOY_DIR}/api", exist_ok=True)
print("  ✓ deployment/ 폴더 생성됨")
print()

# 2. Lambda 레이어 패키징
print("[2/6] Lambda 레이어 패키징...")
print("  - Python 패키지 설치 중...")
subprocess.run([
    "pip", "install", "-r", "requirements.txt",
    "-t", f"{DEPLOY_DIR}/layer/python",
    "--quiet"
])

# ZIP 생성
layer_zip = f"{DEPLOY_DIR}/layer/lambda_layer.zip"
with zipfile.ZipFile(layer_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(f"{DEPLOY_DIR}/layer/python"):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, f"{DEPLOY_DIR}/layer")
            zipf.write(file_path, arcname)

layer_size = os.path.getsize(layer_zip) / (1024 * 1024)
print(f"  ✓ lambda_layer.zip 생성됨 ({layer_size:.2f} MB)")
print()

# 3. Lambda 크롤러 패키징
print("[3/6] Lambda 크롤러 패키징...")
shutil.copy("lambda_crawler.py", f"{DEPLOY_DIR}/crawler/")

crawler_zip = f"{DEPLOY_DIR}/crawler/lambda_crawler.zip"
with zipfile.ZipFile(crawler_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(f"{DEPLOY_DIR}/crawler/lambda_crawler.py", "lambda_crawler.py")

crawler_size = os.path.getsize(crawler_zip) / 1024
print(f"  ✓ lambda_crawler.zip 생성됨 ({crawler_size:.2f} KB)")
print()

# 4. Lambda API 핸들러 패키징
print("[4/6] Lambda API 핸들러 패키징...")
shutil.copy("lambda_api_handlers.py", f"{DEPLOY_DIR}/api/")

api_zip = f"{DEPLOY_DIR}/api/lambda_api.zip"
with zipfile.ZipFile(api_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(f"{DEPLOY_DIR}/api/lambda_api_handlers.py", "lambda_api_handlers.py")

api_size = os.path.getsize(api_zip) / 1024
print(f"  ✓ lambda_api.zip 생성됨 ({api_size:.2f} KB)")
print()

# 5. 완료
print("[5/6] 배포 준비 완료!")
print()
print("=" * 50)
print("생성된 파일:")
print(f"  - {layer_zip}")
print(f"  - {crawler_zip}")
print(f"  - {api_zip}")
print("=" * 50)
print()

print("다음 단계:")
print("  1. AWS 콘솔 접속: https://console.aws.amazon.com")
print("  2. Lambda → 레이어 → lambda_layer.zip 업로드")
print("  3. Lambda → 함수 생성 → ZIP 파일들 업로드")
print()
print("자세한 가이드: AWS_V0_INTEGRATION_GUIDE.md")
