#!/usr/bin/env python3
"""
버그 체크 스크립트
"""
import os
import re

def check_file_syntax(filepath):
    """파일 구문 기본 체크"""
    errors = []

    if not os.path.exists(filepath):
        return [f"파일 없음: {filepath}"]

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

        # JSX/JS 기본 체크
        if filepath.endswith('.js'):
            # import 누락 체크
            if 'Haptics' in content and 'import * as Haptics' not in content:
                errors.append("Haptics import 누락 가능")

            # 괄호 균형 체크 (간단)
            open_count = content.count('{')
            close_count = content.count('}')
            if open_count != close_count:
                errors.append(f"중괄호 불균형: {{ {open_count} vs }} {close_count}")

            # useEffect 의존성 경고 체크
            if 'useEffect' in content:
                # loadNotams가 있는지 확인
                if 'loadNotams()' in content and 'useEffect' in content:
                    errors.append("INFO: useEffect에서 loadNotams 호출 - 의존성 확인 필요")

        # Python 기본 체크
        if filepath.endswith('.py'):
            if content.strip() == '':
                errors.append("빈 파일")

    return errors

def main():
    print("=" * 80)
    print("버그 체크 시작")
    print("=" * 80)

    files_to_check = [
        'notam-app/src/screens/ImprovedMapScreen.js',
        'notam-app/src/utils/notamParser.js',
        'notam_crawler_api.py',
    ]

    all_ok = True
    for filepath in files_to_check:
        print(f"\n[체크] {filepath}")
        errors = check_file_syntax(filepath)

        if errors:
            all_ok = False
            for error in errors:
                print(f"  [WARNING] {error}")
        else:
            print(f"  [OK] No issues")

    print("\n" + "=" * 80)
    if all_ok:
        print("[OK] All files checked - No issues!")
    else:
        print("[WARNING] Some files have warnings. Please check above.")
    print("=" * 80)

if __name__ == "__main__":
    main()
