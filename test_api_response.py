#!/usr/bin/env python3
"""API 응답 필드 확인"""
from notam_crawler_api import NOTAMCrawlerAPI

crawler = NOTAMCrawlerAPI()

# 1페이지만 가져오기
payload = crawler.get_search_payload(
    data_source='domestic',
    hours_back=720,  # 30일
    page=1,
    rows_per_page=5
)

response = crawler.session.post(crawler.search_endpoint, data=payload, timeout=30)

print("=" * 80)
print("API 응답 필드 확인")
print("=" * 80)

try:
    json_data = response.json()
    print("\n1. JSON 최상위 키:", list(json_data.keys()))

    if 'DATA' in json_data and len(json_data['DATA']) > 0:
        print(f"\n2. DATA 항목 수: {len(json_data['DATA'])}")
        
        first_notam = json_data['DATA'][0]
        print("\n3. 모든 필드명:")
        for key in sorted(first_notam.keys()):
            print(f"   - {key}")
        
        print("\n4. NOTAM 번호 관련 필드 값:")
        for key in first_notam.keys():
            if any(x in key.upper() for x in ['NO', 'NUM', 'ID', 'NAME']):
                print(f"   {key} = {first_notam[key]}")
                
except Exception as e:
    print(f"오류: {e}")
    import traceback
    traceback.print_exc()

crawler.close()
