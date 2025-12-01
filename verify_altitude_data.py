#!/usr/bin/env python3
"""
고도 데이터 검증 스크립트
데이터베이스의 고도 값이 제대로 파싱되어 있는지 확인
"""
import sqlite3
import json

def verify_altitude_data():
    conn = sqlite3.connect('notam_realtime.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("NOTAM 고도 데이터 검증")
    print("=" * 80)

    # 1. 전체 통계
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT lower_limit) as distinct_lower,
            COUNT(DISTINCT upper_limit) as distinct_upper
        FROM notams
    """)
    total, distinct_lower, distinct_upper = cursor.fetchone()
    print(f"\n📊 전체 통계:")
    print(f"   총 NOTAM 개수: {total}")
    print(f"   하한 고도 종류: {distinct_lower}")
    print(f"   상한 고도 종류: {distinct_upper}")

    # 2. 고도 분포
    print(f"\n📈 상한 고도 분포:")
    cursor.execute("""
        SELECT upper_limit, COUNT(*) as count
        FROM notams
        GROUP BY upper_limit
        ORDER BY count DESC
        LIMIT 15
    """)
    for upper, count in cursor.fetchall():
        print(f"   {upper}: {count}개")

    # 3. 샘플 데이터 (고도가 다양한 경우)
    print(f"\n🔍 샘플 데이터 (다양한 고도):")
    cursor.execute("""
        SELECT notam_number, lower_limit, upper_limit, q_code, airport_icao
        FROM notams
        WHERE upper_limit IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 10
    """)
    for row in cursor.fetchall():
        notam_num, lower, upper, qcode, airport = row
        qcode_short = qcode[:50] + "..." if qcode and len(qcode) > 50 else qcode
        print(f"   {notam_num} [{airport}]: {lower}-{upper}ft")
        if qcode:
            print(f"      Q: {qcode_short}")

    # 4. 000/999 패턴 확인
    cursor.execute("""
        SELECT COUNT(*)
        FROM notams
        WHERE lower_limit = 0 AND upper_limit = 999
    """)
    count_000_999 = cursor.fetchone()[0]
    print(f"\n⚠️  000/999 패턴:")
    print(f"   하한 0ft, 상한 999ft인 NOTAM: {count_000_999}개 ({count_000_999/total*100:.1f}%)")

    # 5. 고도 범위별 분류
    print(f"\n🎯 고도 범위별 분류:")
    cursor.execute("""
        SELECT
            CASE
                WHEN upper_limit IS NULL THEN '정보없음'
                WHEN upper_limit >= 10000 THEN '높음(≥10K ft)'
                WHEN upper_limit >= 3000 THEN '중간(3-10K ft)'
                ELSE '낮음(<3K ft)'
            END as category,
            COUNT(*) as count
        FROM notams
        GROUP BY category
        ORDER BY count DESC
    """)
    for category, count in cursor.fetchall():
        print(f"   {category}: {count}개 ({count/total*100:.1f}%)")

    # 6. Q-Code에서 고도 확인 (샘플)
    print(f"\n🔬 Q-Code 고도 파싱 검증:")
    cursor.execute("""
        SELECT notam_number, q_code, lower_limit, upper_limit
        FROM notams
        WHERE q_code LIKE 'Q)%'
        LIMIT 5
    """)
    for notam_num, qcode, lower, upper in cursor.fetchall():
        # Q-Code 파싱
        parts = qcode.split('/')
        if len(parts) >= 7:
            qcode_lower = parts[5]  # 5번째 필드
            qcode_upper = parts[6]  # 6번째 필드
            print(f"   {notam_num}:")
            print(f"      Q-Code: {qcode_lower}/{qcode_upper}")
            print(f"      DB 저장: {lower}/{upper}ft")

            # 검증 (Q-Code는 Flight Level, DB는 feet)
            # FL000 = SFC/GND, FL999 = Unlimited
            if qcode_lower == "000" and lower == 0:
                print(f"      ✅ 하한 일치 (SFC/GND)")
            if qcode_upper == "999" and upper == 99900:
                print(f"      ✅ 상한 일치 (Unlimited)")
            elif qcode_upper.isdigit():
                expected_upper = int(qcode_upper) * 100
                if upper == expected_upper:
                    print(f"      ✅ 상한 일치 (FL{qcode_upper} = {expected_upper}ft)")
                else:
                    print(f"      ⚠️ 상한 불일치 (예상: {expected_upper}ft, 실제: {upper}ft)")

    conn.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    verify_altitude_data()
