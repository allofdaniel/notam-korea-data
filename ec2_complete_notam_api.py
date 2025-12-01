"""
EC2 완전 NOTAM API 서버
S3에서 154,986개 전체 NOTAM 제공
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

s3 = boto3.client('s3')
BUCKET_NAME = 'notam-korea-data'
COMPLETE_DATA_KEY = 'notam_complete/20251201_100751/notam_final_complete.json'

# 전체 NOTAM 캐시 (서버 시작 시 한 번만 로드)
ALL_NOTAMS = None

def load_all_notams():
    """S3에서 전체 NOTAM 로드 (한 번만)"""
    global ALL_NOTAMS
    if ALL_NOTAMS is not None:
        return ALL_NOTAMS

    print(f"[LOAD] S3에서 전체 NOTAM 로드 중: {COMPLETE_DATA_KEY}")
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=COMPLETE_DATA_KEY)
    ALL_NOTAMS = json.loads(obj['Body'].read().decode('utf-8'))
    print(f"[OK] {len(ALL_NOTAMS)}개 NOTAM 로드 완료")
    return ALL_NOTAMS

def parse_notam_date(date_str):
    """NOTAM 날짜 파싱 (YYMMDDHHMM 형식)"""
    if not date_str or len(date_str) < 8:
        return None
    try:
        year = int('20' + date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        hour = int(date_str[6:8]) if len(date_str) >= 8 else 0
        minute = int(date_str[8:10]) if len(date_str) >= 10 else 0
        return datetime(year, month, day, hour, minute)
    except:
        return None

def get_notam_status(notam, current_time=None):
    """NOTAM 상태 분류"""
    if current_time is None:
        current_time = datetime.now()

    effective_start = parse_notam_date(notam.get('effective_start', ''))
    effective_end = parse_notam_date(notam.get('effective_end', ''))

    # 트리거 NOTAM 체크
    e_text = notam.get('e_text', '').upper()
    trigger_keywords = ['TRIGGER', 'NOTAM TO FOLLOW', 'NEW NOTAM', 'WILL TAKE PLACE']
    is_trigger = any(keyword in e_text for keyword in trigger_keywords)

    if is_trigger:
        return 'trigger'

    if not effective_end:
        if effective_start and effective_start > current_time:
            return 'scheduled'
        return 'active'

    if effective_start and effective_start > current_time:
        return 'scheduled'

    if effective_end < current_time:
        return 'expired'

    return 'active'

def categorize_notams(notams, filter_date=None):
    """NOTAM 분류 및 통계"""
    current_time = datetime.now()

    # 날짜 필터링
    if filter_date:
        try:
            filter_dt = datetime.strptime(filter_date, '%Y-%m-%d')
            notams = [n for n in notams if n.get('crawl_date', '').startswith(filter_date)]
        except:
            pass

    categorized = {
        'active': [],
        'expired': [],
        'trigger': [],
        'scheduled': []
    }

    for notam in notams:
        status = get_notam_status(notam, current_time)
        categorized[status].append({
            **notam,
            'status': status
        })

    stats = {
        'total': len(notams),
        'active': len(categorized['active']),
        'expired': len(categorized['expired']),
        'trigger': len(categorized['trigger']),
        'scheduled': len(categorized['scheduled']),
        'filter_date': filter_date,
        'current_time': current_time.isoformat()
    }

    return categorized, stats

# ===== API 엔드포인트 =====

@app.route('/notams/stats', methods=['GET'])
def get_stats():
    """전체 통계"""
    filter_date = request.args.get('date')
    all_notams = load_all_notams()
    _, stats = categorize_notams(all_notams, filter_date)
    return jsonify(stats)

@app.route('/notams/active', methods=['GET'])
def get_active():
    """활성 NOTAM"""
    filter_date = request.args.get('date')
    all_notams = load_all_notams()
    categorized, stats = categorize_notams(all_notams, filter_date)

    return jsonify({
        'stats': stats,
        'data': categorized['active']
    })

@app.route('/notams/expired', methods=['GET'])
def get_expired():
    """만료 NOTAM"""
    filter_date = request.args.get('date')
    all_notams = load_all_notams()
    categorized, stats = categorize_notams(all_notams, filter_date)

    return jsonify({
        'stats': stats,
        'data': categorized['expired']
    })

@app.route('/notams/trigger', methods=['GET'])
def get_trigger():
    """트리거 NOTAM"""
    filter_date = request.args.get('date')
    all_notams = load_all_notams()
    categorized, stats = categorize_notams(all_notams, filter_date)

    return jsonify({
        'stats': stats,
        'data': categorized['trigger']
    })

@app.route('/notams/complete', methods=['GET'])
def get_complete():
    """전체 NOTAM (분류됨)"""
    filter_date = request.args.get('date')
    limit = int(request.args.get('limit', 1000))

    all_notams = load_all_notams()
    categorized, stats = categorize_notams(all_notams, filter_date)

    result = {
        'stats': stats,
        'categorized': {
            'active': categorized['active'][:limit],
            'expired': categorized['expired'][:limit],
            'trigger': categorized['trigger'][:limit],
            'scheduled': categorized['scheduled'][:limit]
        }
    }

    return jsonify(result)

@app.route('/notams/date/<date>', methods=['GET'])
def get_by_date(date):
    """특정 날짜 NOTAM"""
    all_notams = load_all_notams()
    categorized, stats = categorize_notams(all_notams, date)

    return jsonify({
        'stats': stats,
        'categorized': categorized
    })

@app.route('/health', methods=['GET'])
def health():
    """헬스 체크"""
    all_notams = load_all_notams()
    return jsonify({
        'status': 'ok',
        'total_notams': len(all_notams),
        'server_time': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("=" * 60)
    print("EC2 완전 NOTAM API 서버")
    print("=" * 60)

    # 서버 시작 시 데이터 로드
    load_all_notams()

    print("\n엔드포인트:")
    print("  GET /notams/stats")
    print("  GET /notams/active")
    print("  GET /notams/expired")
    print("  GET /notams/trigger")
    print("  GET /notams/complete")
    print("  GET /notams/date/<date>")
    print("  GET /health")
    print("\n서버 시작 중...\n")

    app.run(host='0.0.0.0', port=8000, debug=False)
