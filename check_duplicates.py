#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('notam_realtime.db')
cursor = conn.cursor()

# 전체 개수
cursor.execute('SELECT COUNT(*) FROM notams')
total = cursor.fetchone()[0]

# Unique 개수
cursor.execute('SELECT COUNT(DISTINCT notam_number) FROM notams')
unique = cursor.fetchone()[0]

# 중복 개수
duplicates = total - unique

print(f"전체 NOTAM: {total}개")
print(f"Unique NOTAM: {unique}개")
print(f"중복 제거됨: {duplicates}개")

if duplicates == 0:
    print("\n✅ 중복 없음 - 완벽하게 작동 중!")
else:
    print(f"\n⚠️ {duplicates}개의 중복이 있습니다")

# 가장 최근 10개
print("\n📋 최근 10개 NOTAM:")
cursor.execute("SELECT notam_number, a_location, substr(e_text, 1, 50) FROM notams ORDER BY last_updated DESC LIMIT 10")
for i, (num, loc, text) in enumerate(cursor.fetchall(), 1):
    print(f"  {i}. {num} ({loc}): {text}...")

conn.close()
