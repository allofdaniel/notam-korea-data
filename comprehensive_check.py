#!/usr/bin/env python3
"""
전체 작업 종합 검토
"""
import os
import subprocess
import json

def check_file_exists(filepath):
    """파일 존재 확인"""
    return os.path.exists(filepath)

def check_imports(filepath):
    """Import 구문 확인"""
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []

    # Haptics 사용하지만 import 안 했는지
    if 'Haptics.' in content and 'import * as Haptics' not in content:
        issues.append("Haptics 사용하지만 import 누락")

    # Animated 사용하지만 import 안 했는지
    if 'Animated.' in content and 'Animated' not in content.split('import')[0:2]:
        # 이미 import되어 있을 수 있으므로 더 정확히 체크
        if 'import' in content and 'Animated' in content:
            pass
        else:
            issues.append("Animated 사용 가능성, import 확인 필요")

    # ClusteredMapView import 확인
    if 'ClusteredMapView' in content and 'react-native-map-clustering' not in content:
        issues.append("ClusteredMapView 사용하지만 import 누락 가능")

    return issues

def check_syntax_errors(filepath):
    """기본 구문 오류 체크"""
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []

    # 괄호 균형
    if filepath.endswith('.js'):
        open_paren = content.count('(')
        close_paren = content.count(')')
        open_brace = content.count('{')
        close_brace = content.count('}')
        open_bracket = content.count('[')
        close_bracket = content.count(']')

        if open_paren != close_paren:
            issues.append(f"소괄호 불균형: ( {open_paren} vs ) {close_paren}")
        if open_brace != close_brace:
            issues.append(f"중괄호 불균형: {{ {open_brace} vs }} {close_brace}")
        if open_bracket != close_bracket:
            issues.append(f"대괄호 불균형: [ {open_bracket} vs ] {close_bracket}")

    return issues

def check_db_data():
    """데이터베이스 데이터 확인"""
    import sqlite3

    try:
        conn = sqlite3.connect('notam_realtime.db')
        cursor = conn.cursor()

        # notams 테이블 확인
        cursor.execute("SELECT COUNT(*) FROM notams")
        count = cursor.fetchone()[0]

        # 고도 데이터 확인
        cursor.execute("""
            SELECT COUNT(*)
            FROM notams
            WHERE f_lower_limit IS NOT NULL AND g_upper_limit IS NOT NULL
        """)
        altitude_count = cursor.fetchone()[0]

        conn.close()

        return {
            'total': count,
            'with_altitude': altitude_count,
            'percentage': (altitude_count / count * 100) if count > 0 else 0
        }
    except Exception as e:
        return {'error': str(e)}

def check_package_json():
    """package.json에 필요한 패키지가 있는지 확인"""
    filepath = 'notam-app/package.json'
    if not os.path.exists(filepath):
        return {'error': 'package.json not found'}

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    required = {
        'expo-haptics': False,
        'react-native-map-clustering': False,
        'react-native-maps': False,
    }

    deps = data.get('dependencies', {})
    for pkg in required.keys():
        if pkg in deps:
            required[pkg] = True

    return required

def main():
    print("=" * 80)
    print("전체 작업 종합 검토")
    print("=" * 80)

    # 1. 주요 파일 존재 확인
    print("\n[1] 주요 파일 존재 확인")
    files = {
        'ImprovedMapScreen.js': 'notam-app/src/screens/ImprovedMapScreen.js',
        'notamParser.js': 'notam-app/src/utils/notamParser.js',
        'notam_crawler_api.py': 'notam_crawler_api.py',
        'FINAL_COMPLETION_REPORT.md': 'FINAL_COMPLETION_REPORT.md',
    }

    for name, path in files.items():
        exists = check_file_exists(path)
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {status} {name}")

    # 2. Import 구문 확인
    print("\n[2] Import 구문 확인")
    for name, path in files.items():
        if path.endswith('.js'):
            issues = check_imports(path)
            if issues:
                print(f"  [WARNING] {name}:")
                for issue in issues:
                    print(f"    - {issue}")
            else:
                print(f"  [OK] {name}")

    # 3. 구문 오류 확인
    print("\n[3] 구문 오류 확인")
    for name, path in files.items():
        if path.endswith('.js'):
            issues = check_syntax_errors(path)
            if issues:
                print(f"  [ERROR] {name}:")
                for issue in issues:
                    print(f"    - {issue}")
            else:
                print(f"  [OK] {name}")

    # 4. 데이터베이스 확인
    print("\n[4] 데이터베이스 확인")
    db_info = check_db_data()
    if 'error' in db_info:
        print(f"  [ERROR] {db_info['error']}")
    else:
        print(f"  [INFO] 총 NOTAM: {db_info['total']}개")
        print(f"  [INFO] 고도 데이터 있음: {db_info['with_altitude']}개 ({db_info['percentage']:.1f}%)")

        if db_info['total'] < 100:
            print(f"  [WARNING] NOTAM 데이터가 너무 적습니다! (현재: {db_info['total']}개, 권장: 1000+개)")
        if db_info['percentage'] < 50:
            print(f"  [WARNING] 고도 데이터 비율이 낮습니다!")

    # 5. package.json 확인
    print("\n[5] 필수 패키지 확인")
    packages = check_package_json()
    if 'error' in packages:
        print(f"  [ERROR] {packages['error']}")
    else:
        for pkg, installed in packages.items():
            status = "[OK]" if installed else "[MISSING]"
            print(f"  {status} {pkg}")

    # 6. 미완성 작업 확인
    print("\n[6] 미완성 작업 확인")
    todos = [
        ("성능 최적화", "미구현 - 5000+ NOTAM 대비 최적화 필요"),
        ("고도 필터 UI", "로직만 구현됨 - UI 버튼 필요"),
        ("더 많은 데이터", "79개는 부족 - 1000+ 개 필요"),
        ("실제 앱 테스트", "코드만 작성, 실제 실행 미확인"),
        ("Web Callout", "선택사항 - 구현 안 함"),
    ]

    for task, status in todos:
        print(f"  [TODO] {task}: {status}")

    print("\n" + "=" * 80)
    print("검토 완료")
    print("=" * 80)

if __name__ == "__main__":
    main()
