#!/usr/bin/env python3
"""
고도 파싱 결과 확인
"""
import sqlite3

conn = sqlite3.connect('notam_realtime.db')
cursor = conn.cursor()

print("=" * 80)
print("고도 파싱 결과 확인")
print("=" * 80)

# notams 테이블 확인
cursor.execute("SELECT COUNT(*) FROM notams")
count = cursor.fetchone()[0]
print(f"\n총 NOTAM 개수: {count}개")

# 샘플 데이터 확인 (고도 정보 포함)
print("\n샘플 NOTAM (고도 정보):")
cursor.execute("""
    SELECT
        notam_number,
        a_location,
        f_lower_limit,
        g_upper_limit,
        q_code,
        full_text
    FROM notams
    LIMIT 5
""")

for row in cursor.fetchall():
    notam_num, location, f_lower, g_upper, qcode, full_text = row
    print(f"\n[{notam_num}] {location}")
    print(f"  고도: {f_lower} - {g_upper}")
    print(f"  Q-Code: {qcode}")

    # Q-Code에서 고도 추출
    if qcode and '/' in qcode:
        # full_text_detail에서 Q) 라인 찾기
        q_line = None
        if full_text:
            for line in full_text.split('\n'):
                if line.startswith('Q)'):
                    q_line = line
                    break

        if q_line:
            parts = q_line.split('/')
            if len(parts) >= 7:
                print(f"  Q-Line: {q_line}")
                print(f"  파싱된 Lower: {parts[5]}, Upper: {parts[6][:3] if len(parts[6]) >= 3 else parts[6]}")

# 고도 분포 확인
print("\n" + "=" * 80)
print("고도 상한 분포:")
cursor.execute("""
    SELECT g_upper_limit, COUNT(*) as count
    FROM notams
    WHERE g_upper_limit IS NOT NULL AND g_upper_limit != ''
    GROUP BY g_upper_limit
    ORDER BY count DESC
""")

for upper, cnt in cursor.fetchall():
    print(f"  {upper}: {cnt}개")

conn.close()
print("\n" + "=" * 80)
