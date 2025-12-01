"""
Lambda 함수 패키징 (간단 버전)
"""

import zipfile
import os

def package_lambda_crawler():
    """Lambda 크롤러 ZIP 생성"""

    print("Lambda 크롤러 패키징 중...")

    # 배포 디렉토리 생성
    os.makedirs('deployment', exist_ok=True)

    # ZIP 파일 생성
    zip_path = 'deployment/lambda_crawler.zip'

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write('lambda_crawler.py', 'lambda_crawler.py')

    file_size = os.path.getsize(zip_path)
    print(f"완료: {zip_path} ({file_size:,} bytes)")

    return zip_path


if __name__ == '__main__':
    package_lambda_crawler()
    print("\n다음 단계:")
    print("  1. AWS Lambda 콘솔로 이동")
    print("  2. lambda-notam-crawler 함수 선택")
    print("  3. 코드 소스 > Upload from > .zip file")
    print("  4. deployment/lambda_crawler.zip 업로드")
