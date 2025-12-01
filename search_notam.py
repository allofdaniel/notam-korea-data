#!/usr/bin/env python3
"""NOTAM 검색 도구"""
import sqlite3
import sys

def search_notam(keyword=None, year=None, series=None, location=None, limit=20):
    """NOTAM 검색"""
    conn = sqlite3.connect('notam_final_all.db')
    cursor = conn.cursor()
    
    query = "SELECT notam_number, a_location, series_type, e_text, crawl_date FROM notams WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND (notam_number LIKE ? OR e_text LIKE ?)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    
    if year:
        query += " AND year = ?"
        params.append(year)
    
    if series:
        query += " AND series_type = ?"
        params.append(series)
    
    if location:
        query += " AND a_location LIKE ?"
        params.append(f'%{location}%')
    
    query += f" ORDER BY crawl_date DESC LIMIT {limit}"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    print("=" * 80)
    print(f"검색 결과: {len(results)}개")
    print("=" * 80)
    
    for row in results:
        notam_no, location, series, text, date = row
        text_preview = text[:50] + '...' if text and len(text) > 50 else text
        print(f"\n{notam_no} | {location} | {series} | {date}")
        print(f"  {text_preview}")
    
    conn.close()
    print("\n" + "=" * 80)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 명령줄 인자로 검색
        keyword = sys.argv[1] if len(sys.argv) > 1 else None
        search_notam(keyword=keyword)
    else:
        # 대화형 검색
        print("=" * 80)
        print("NOTAM 검색")
        print("=" * 80)
        print("\n검색 옵션 (Enter로 건너뛰기):")
        
        keyword = input("키워드: ").strip() or None
        year_input = input("연도 (2022/2023/2024/2025): ").strip()
        year = int(year_input) if year_input else None
        series = input("시리즈 (A/C/D/E/G/Z 등): ").strip().upper() or None
        location = input("공항/위치: ").strip().upper() or None
        
        search_notam(keyword=keyword, year=year, series=series, location=location)
