#!/usr/bin/env python3
"""
NOTAM API Server for EC2
간단한 Flask API 서버 + Google Gemini NOTAM 해석
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timedelta
import google.generativeai as genai

app = Flask(__name__)
CORS(app)  # 모든 도메인에서 접근 허용

DB_PATH = 'notam_realtime.db'

# Google Gemini API 설정
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyA7zE8nqLkNcSXjHPX9AVOZues3BsNczbA')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # 가장 빠른 모델 사용
    gemini_model = genai.GenerativeModel('gemini-2.0-flash')
else:
    gemini_model = None

def get_db_connection():
    """데이터베이스 연결"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': os.path.exists(DB_PATH)
    })

@app.route('/api/notams', methods=['GET'])
def get_all_notams():
    """모든 NOTAM 조회 (전체 - LIMIT 제거)"""
    try:
        conn = get_db_connection()
        # LIMIT 제거하여 전체 NOTAM 반환 (5,655개)
        notams = conn.execute('SELECT * FROM notams ORDER BY b_start_time DESC').fetchall()
        conn.close()

        return jsonify([dict(row) for row in notams])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notams/<icao>', methods=['GET'])
def get_notams_by_airport(icao):
    """특정 공항 NOTAM 조회"""
    try:
        conn = get_db_connection()
        notams = conn.execute(
            'SELECT * FROM notams WHERE a_location = ? ORDER BY b_start_time DESC',
            (icao.upper(),)
        ).fetchall()
        conn.close()

        return jsonify([dict(row) for row in notams])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notam/<int:notam_id>', methods=['GET'])
def get_notam_detail(notam_id):
    """특정 NOTAM 상세 조회"""
    try:
        conn = get_db_connection()
        notam = conn.execute('SELECT * FROM notams WHERE id = ?', (notam_id,)).fetchone()
        conn.close()

        if notam:
            return jsonify(dict(notam))
        else:
            return jsonify({'error': 'NOTAM not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/active', methods=['GET'])
@app.route('/api/active/<icao>', methods=['GET'])
def get_active_notams(icao=None):
    """활성 NOTAM 조회"""
    try:
        conn = get_db_connection()
        now = datetime.utcnow().isoformat()

        if icao:
            query = '''
                SELECT * FROM notams
                WHERE a_location = ?
                AND (c_end_time IS NULL OR c_end_time > ?)
                ORDER BY b_start_time DESC
            '''
            notams = conn.execute(query, (icao.upper(), now)).fetchall()
        else:
            query = '''
                SELECT * FROM notams
                WHERE c_end_time IS NULL OR c_end_time > ?
                ORDER BY b_start_time DESC
            '''
            notams = conn.execute(query, (now,)).fetchall()

        conn.close()
        return jsonify([dict(row) for row in notams])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent/<int:hours>', methods=['GET'])
def get_recent_notams(hours):
    """최근 N시간 NOTAM 조회 (전체)"""
    try:
        conn = get_db_connection()
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        query = '''
            SELECT * FROM notams
            WHERE collected_at > ?
            ORDER BY collected_at DESC
        '''
        notams = conn.execute(query, (cutoff_time,)).fetchall()
        conn.close()

        return jsonify([dict(row) for row in notams])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_notams():
    """NOTAM 검색"""
    try:
        query_text = request.args.get('q', '')
        if not query_text:
            return jsonify({'error': 'Query parameter "q" is required'}), 400

        conn = get_db_connection()
        query = '''
            SELECT * FROM notams
            WHERE e_text LIKE ? OR a_location LIKE ?
            ORDER BY b_start_time DESC
            LIMIT 100
        '''
        search_pattern = f'%{query_text}%'
        notams = conn.execute(query, (search_pattern, search_pattern)).fetchall()
        conn.close()

        return jsonify([dict(row) for row in notams])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """통계 정보"""
    try:
        conn = get_db_connection()

        # 전체 NOTAM 수
        total = conn.execute('SELECT COUNT(*) as count FROM notams').fetchone()['count']

        # 활성 NOTAM 수
        now = datetime.utcnow().isoformat()
        active = conn.execute(
            'SELECT COUNT(*) as count FROM notams WHERE c_end_time IS NULL OR c_end_time > ?',
            (now,)
        ).fetchone()['count']

        # 공항별 NOTAM 수
        by_airport = conn.execute('''
            SELECT a_location, COUNT(*) as count
            FROM notams
            GROUP BY a_location
            ORDER BY count DESC
        ''').fetchall()

        conn.close()

        return jsonify({
            'total': total,
            'active': active,
            'by_airport': [dict(row) for row in by_airport]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/translate', methods=['POST'])
def interpret_notam():
    """NOTAM 해석 (Google Gemini 사용) - 항공 전문가가 아닌 사람도 이해 가능하게"""
    try:
        data = request.get_json()
        notam_text = data.get('text', '')
        context = data.get('context', {})

        if not notam_text:
            return jsonify({'error': 'NOTAM text is required'}), 400

        # Gemini API로 NOTAM 해석
        if gemini_model:
            try:
                prompt = f"""다음 NOTAM을 1-2문장으로 간단명료하게 요약해주세요.

공항: {context.get('airport', 'N/A')}
원문: {notam_text}

답변 형식 (반드시 짧게):
1. 한글 해석: (핵심만 1문장)
2. 쉬운 설명: (영향과 주의사항 1-2문장)
3. 한 줄 요약: (10자 이내)"""

                response = gemini_model.generate_content(prompt)
                response_text = response.text

                # 응답 파싱 - 더 견고하게
                interpreted = ""
                explanation = ""
                summary = ""

                # 섹션별로 분리
                text = response_text.strip()

                # 1. 한글 해석 찾기
                if '1.' in text or '한글 해석' in text:
                    parts = text.split('2.')
                    if len(parts) > 0:
                        first_part = parts[0]
                        # 첫 번째 콜론 이후 전체를 가져옴
                        if ':' in first_part:
                            interpreted = first_part.split(':', 1)[1].strip()
                        else:
                            interpreted = first_part.replace('1.', '').replace('한글 해석', '').strip()

                # 2. 쉬운 설명 찾기
                if '2.' in text or '쉬운 설명' in text:
                    if '2.' in text:
                        parts = text.split('2.')[1].split('3.')
                    else:
                        parts = text.split('쉬운 설명')[1].split('3.')

                    if len(parts) > 0:
                        explanation_part = parts[0]
                        if ':' in explanation_part:
                            explanation = explanation_part.split(':', 1)[1].strip()
                        else:
                            explanation = explanation_part.strip()

                # 3. 요약 찾기
                if '3.' in text or '한 줄 요약' in text or '요약:' in text:
                    if '3.' in text:
                        summary_part = text.split('3.')[1]
                    elif '한 줄 요약' in text:
                        summary_part = text.split('한 줄 요약')[1]
                    else:
                        summary_part = text.split('요약:')[1]

                    if ':' in summary_part:
                        summary = summary_part.split(':', 1)[1].strip()
                    else:
                        summary = summary_part.strip()

                return jsonify({
                    'translated': interpreted or response_text,
                    'explanation': explanation,
                    'summary': summary,
                    'isBasicTranslation': False
                })

            except Exception as e:
                print(f"Gemini API error: {e}")
                import traceback
                traceback.print_exc()
                # Gemini API 실패시 기본 해석으로 폴백
                pass

        # 기본 해석 (Gemini API 없을 때)
        return jsonify(fallback_translation(notam_text, context))

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def fallback_translation(notam_text, context):
    """기본 번역 함수 (Claude API 없을 때)"""
    aviation_terms = {
        'RWY': '활주로', 'RUNWAY': '활주로',
        'TWY': '유도로', 'TAXIWAY': '유도로',
        'APRON': '계류장', 'CLSD': '폐쇄됨', 'CLOSED': '폐쇄됨',
        'OBST': '장애물', 'OBSTACLE': '장애물',
        'ILS': '계기착륙장치', 'VOR': 'VOR 항행안전시설',
        'DME': '거리측정장비', 'PAPI': '진입각지시등',
        'AVBL': '이용 가능', 'AVAILABLE': '이용 가능',
        'U/S': '사용 불가', 'UNSERVICEABLE': '사용 불가',
        'WIP': '공사 중', 'WORK IN PROGRESS': '공사 중',
    }

    translated = notam_text
    for eng, kor in aviation_terms.items():
        import re
        translated = re.sub(rf'\b{eng}\b', kor, translated, flags=re.IGNORECASE)

    # 간단한 설명 생성
    lower = notam_text.lower()
    airport = context.get('airport', '해당 공항')

    if 'rwy' in lower or 'runway' in lower:
        if 'clsd' in lower or 'closed' in lower:
            explanation = f"{airport}의 활주로가 폐쇄되었습니다."
        else:
            explanation = f"{airport}의 활주로 관련 고시입니다."
    elif 'ils' in lower or 'vor' in lower:
        explanation = f"{airport}의 항행안전시설 관련 고시입니다."
    elif 'obst' in lower:
        explanation = f"{airport} 인근에 장애물이 있습니다."
    else:
        explanation = f"{airport}의 운영 정보입니다."

    return {
        'translated': translated,
        'explanation': explanation,
        'summary': f"{airport} 운영 정보",
        'isBasicTranslation': True
    }

if __name__ == '__main__':
    print("🚀 NOTAM API Server Starting...")
    print(f"📊 Database: {DB_PATH}")
    print(f"🌐 Server will run on http://0.0.0.0:8000")

    # 데이터베이스 확인
    if not os.path.exists(DB_PATH):
        print(f"⚠️  Warning: Database file not found at {DB_PATH}")

    app.run(host='0.0.0.0', port=8000, debug=False)
