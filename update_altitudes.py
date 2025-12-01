#!/usr/bin/env python3
"""
기존 NOTAM의 고도 정보를 full_text에서 추출하여 업데이트
"""
import sqlite3

def update_altitudes():
    conn = sqlite3.connect('notam_realtime.db')
    cursor = conn.cursor()

    # 고도 정보가 없는 NOTAM 가져오기
    cursor.execute("""
        SELECT id, full_text
        FROM notams
        WHERE (f_lower_limit = '' OR f_lower_limit IS NULL)
    """)
    notams = cursor.fetchall()

    print(f'처리할 NOTAM: {len(notams)}개')

    updated = 0
    for notam_id, full_text in notams:
        if not full_text or 'Q)' not in full_text:
            continue

        # Q-Code 라인 찾기
        q_line = ''
        for line in full_text.split('\n'):
            if line.strip().startswith('Q)'):
                q_line = line
                break

        if q_line:
            parts = q_line.split('/')
            if len(parts) >= 7:
                f_lower = parts[5] if parts[5] != '000' else 'SFC'
                g_upper = parts[6][:3] if len(parts) > 6 else ''

                cursor.execute("""
                    UPDATE notams
                    SET f_lower_limit = ?, g_upper_limit = ?
                    WHERE id = ?
                """, (f_lower, g_upper, notam_id))
                updated += 1

                if updated % 100 == 0:
                    print(f'진행 중... {updated}개 업데이트됨')

    conn.commit()
    print(f'\n✅ {updated}개 NOTAM의 고도 정보 업데이트 완료!')

    # 결과 확인
    cursor.execute("""
        SELECT COUNT(*)
        FROM notams
        WHERE f_lower_limit != '' AND f_lower_limit IS NOT NULL
    """)
    total_with_alt = cursor.fetchone()[0]
    print(f'📊 고도 정보가 있는 NOTAM: {total_with_alt}개')

    # 샘플 확인
    cursor.execute("""
        SELECT notam_number, a_location, f_lower_limit, g_upper_limit
        FROM notams
        WHERE f_lower_limit != '' AND f_lower_limit IS NOT NULL
        ORDER BY id DESC
        LIMIT 5
    """)
    print(f'\n최신 5개 샘플:')
    for row in cursor.fetchall():
        print(f'  {row[0]} ({row[1]}): {row[2]} ~ {row[3]}')

    conn.close()

if __name__ == '__main__':
    update_altitudes()
