"""하이브리드 크롤러 테스트 (API 모드)"""
from notam_hybrid_crawler import NOTAMHybridCrawler

print("="*70)
print("NOTAM 하이브리드 크롤러 테스트 (API 모드)")
print("="*70)

crawler = NOTAMHybridCrawler()

try:
    # 국내 NOTAM만 테스트 (빠른 테스트)
    result = crawler.crawl_notam('domestic', hours_back=24)

    print(f"\n{'='*70}")
    print(f"테스트 결과:")
    print(f"  상태: {result['status']}")
    print(f"  방법: {result['method']}")
    print(f"  발견: {result['records_found']}개")
    print(f"  저장: {result['records_saved']}개")
    print(f"  시간: {result['execution_time']:.2f}초")

    if result['error']:
        print(f"  에러: {result['error']}")

    print(f"{'='*70}\n")

finally:
    crawler.close()
