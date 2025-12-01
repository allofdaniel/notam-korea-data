import sqlite3
from datetime import datetime

conn = sqlite3.connect('notam_realtime.db')
cursor = conn.cursor()

# Total NOTAMs
cursor.execute('SELECT COUNT(*) FROM notam_records')
total = cursor.fetchone()[0]
print(f'총 NOTAM 개수: {total}')

# Recent NOTAMs
cursor.execute('SELECT notam_number, a_location, q_code, b_start_time FROM notam_records ORDER BY b_start_time DESC LIMIT 5')
print('\n최근 NOTAM 5개:')
for row in cursor.fetchall():
    print(f'  {row[0]} - {row[1]} ({row[2]}) - {row[3]}')

# Active NOTAMs
cursor.execute('''
    SELECT COUNT(*) FROM notam_records
    WHERE datetime(c_end_time) > datetime('now')
       OR c_end_time IS NULL
       OR c_end_time LIKE '%PERM%'
''')
active = cursor.fetchone()[0]
print(f'\n활성 NOTAM 개수: {active}')

# Check for NOTAMs with coordinate data
cursor.execute('SELECT COUNT(*) FROM notam_records WHERE e_text LIKE "%N%E%" OR e_text LIKE "%RADIUS%"')
with_coords = cursor.fetchone()[0]
print(f'좌표 정보가 있는 NOTAM: {with_coords}')

# Check for NOTAMs with altitude data
cursor.execute('SELECT COUNT(*) FROM notam_records WHERE f_lower_limit IS NOT NULL OR f_upper_limit IS NOT NULL')
with_altitude = cursor.fetchone()[0]
print(f'고도 정보가 있는 NOTAM: {with_altitude}')

# Sample NOTAMs with altitude
cursor.execute('''
    SELECT notam_number, q_code, f_lower_limit, f_upper_limit
    FROM notam_records
    WHERE f_upper_limit IS NOT NULL
    ORDER BY CAST(f_upper_limit AS INTEGER) DESC
    LIMIT 5
''')
print('\n고도 정보가 있는 NOTAM 샘플 (높은 고도순):')
for row in cursor.fetchall():
    print(f'  {row[0]} ({row[1]}) - {row[2]} ~ {row[3]} ft')

# Check last crawl time
cursor.execute('SELECT MAX(crawl_time) FROM crawl_logs')
last_crawl = cursor.fetchone()[0]
print(f'\n마지막 크롤링 시간: {last_crawl}')

conn.close()
