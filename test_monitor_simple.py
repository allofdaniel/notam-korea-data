"""간단한 모니터링 시스템 테스트"""
import sys

# logging 에러 방지
import logging
logging.basicConfig(level=logging.WARNING)  # WARNING 이상만 출력

from notam_monitor import NOTAMMonitor

print("="*70)
print("NOTAM 모니터링 시스템 테스트")
print("="*70)

monitor = NOTAMMonitor()

try:
    # 국내 NOTAM만 테스트
    print("\n1. 국내 NOTAM 모니터링 (변경 감지 비활성화)...")
    result = monitor.monitor_single('domestic', hours_back=24, enable_change_detection=False)

    print(f"\n결과:")
    print(f"  상태: {result['status']}")

    if result.get('crawl_result'):
        cr = result['crawl_result']
        print(f"  크롤링: {cr['records_found']}개 발견")
        print(f"  방법: {cr['method']}")
        print(f"  시간: {cr['execution_time']:.2f}초")

    if result.get('change_result'):
        ch = result['change_result']
        print(f"  변경: 신규 {ch['new']}개, 업데이트 {ch['updated']}개")

    # 통계
    print("\n2. 변경 통계 조회...")
    stats = monitor.get_statistics(hours=24)
    print(f"  통계: {stats}")

    print("\n✅ 테스트 완료!")

except Exception as e:
    print(f"\n❌ 테스트 실패: {e}")
    import traceback
    traceback.print_exc()

finally:
    monitor.close()
