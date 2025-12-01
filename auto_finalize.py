#!/usr/bin/env python3
"""
수집 완료 자동 감지 및 후처리
1. 수집 완료 대기
2. 자동 마이그레이션
3. S3 업로드
4. API 서버 재시작
"""
import subprocess
import time
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def is_collection_running():
    """수집이 진행 중인지 확인"""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )

        return 'fast_historical_collector.py' in result.stdout

    except Exception as e:
        logger.error(f"프로세스 확인 실패: {e}")
        return False


def wait_for_completion(check_interval=60):
    """수집 완료 대기"""

    logger.info(f"\n{'='*80}")
    logger.info("⏳ 수집 완료 대기 중...")
    logger.info(f"{'='*80}\n")

    wait_time = 0

    while is_collection_running():
        logger.info(f"  대기 시간: {wait_time // 60}분 {wait_time % 60}초")

        time.sleep(check_interval)
        wait_time += check_interval

    logger.info(f"\n✅ 수집 완료! (총 대기: {wait_time // 60}분)")


def run_migration():
    """통합 마이그레이션 실행"""

    logger.info(f"\n{'='*80}")
    logger.info("🔄 통합 마이그레이션 시작...")
    logger.info(f"{'='*80}\n")

    try:
        result = subprocess.run(
            ["python3", "unified_migration.py"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info(result.stdout)
            logger.info("✅ 마이그레이션 성공!")
            return True
        else:
            logger.error(f"❌ 마이그레이션 실패:\n{result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ 마이그레이션 오류: {e}")
        return False


def upload_to_s3():
    """S3 업로드 실행"""

    logger.info(f"\n{'='*80}")
    logger.info("☁️  S3 업로드 시작...")
    logger.info(f"{'='*80}\n")

    try:
        result = subprocess.run(
            ["python3", "upload_to_s3.py"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info(result.stdout)
            logger.info("✅ S3 업로드 성공!")
            return True
        else:
            logger.error(f"❌ S3 업로드 실패:\n{result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ S3 업로드 오류: {e}")
        return False


def restart_api_server():
    """API 서버 재시작"""

    logger.info(f"\n{'='*80}")
    logger.info("🔄 API 서버 재시작...")
    logger.info(f"{'='*80}\n")

    try:
        # 기존 서버 중단
        subprocess.run(["pkill", "-f", "ec2_api_server.py"], check=False)
        time.sleep(2)

        # 새 서버 시작
        subprocess.Popen(
            ["nohup", "python3", "ec2_api_server.py"],
            stdout=open('api_server.log', 'w'),
            stderr=subprocess.STDOUT
        )

        time.sleep(3)

        # 확인
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )

        if 'ec2_api_server.py' in result.stdout:
            logger.info("✅ API 서버 재시작 성공!")
            return True
        else:
            logger.error("❌ API 서버 시작 실패")
            return False

    except Exception as e:
        logger.error(f"❌ API 서버 재시작 오류: {e}")
        return False


def main():
    """메인 실행"""

    logger.info(f"\n{'#'*80}")
    logger.info("🚀 자동 완료 및 후처리 시작")
    logger.info(f"{'#'*80}\n")

    # 1. 수집 완료 대기
    wait_for_completion(check_interval=120)  # 2분마다 체크

    # 2. 통합 마이그레이션
    if not run_migration():
        logger.error("❌ 마이그레이션 실패 - 중단")
        return False

    # 3. S3 업로드
    if not upload_to_s3():
        logger.warning("⚠️  S3 업로드 실패 - 계속 진행")

    # 4. API 서버 재시작
    if not restart_api_server():
        logger.warning("⚠️  API 서버 재시작 실패")

    logger.info(f"\n{'#'*80}")
    logger.info("✅ 모든 후처리 완료!")
    logger.info(f"{'#'*80}\n")

    return True


if __name__ == '__main__':
    try:
        if main():
            print("\n✅ 성공!")
            exit(0)
        else:
            print("\n❌ 실패")
            exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 중단됨")
        exit(1)

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
