import sqlite3

conn = sqlite3.connect('notam_realtime.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(notam_records)')
print('notam_records 테이블 컬럼:')
for row in cursor.fetchall():
    print(f'  {row[1]} ({row[2]})')

print('\n첫 5개 NOTAM 데이터:')
cursor.execute('SELECT * FROM notam_records LIMIT 1')
columns = [description[0] for description in cursor.description]
print(f'컬럼: {columns}')

cursor.execute('SELECT * FROM notam_records LIMIT 5')
for row in cursor.fetchall():
    print(f'\n{dict(zip(columns, row))}')

conn.close()
