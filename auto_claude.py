import sys
import time
import os

# ---------------------------------------------------------
# [OS에 따른 라이브러리 설정]
# Windows 사용자는 아래 주석(#)을 풀고 pexpect 대신 wexpect를 사용하세요.
# import wexpect as pexpect
# Mac/Linux 사용자는 아래 줄을 그대로 두세요.
import wexpect as pexpect


# ---------------------------------------------------------

def run_claude_automation():
    # 실행할 명령어 (권한 승인 건너뛰기 옵션 포함)
    # 주의: 스케줄러에서 실행할 때는 claude의 전체 경로를 적어주는 것이 좋습니다.
    # 예: '/usr/local/bin/claude' 또는 'C:\\Users\\...\\claude.exe'
    COMMAND = "C:\\Users\\allof\\AppData\\Roaming\\npm\\claude.cmd --dangerously-skip-permissions"# 보낼 메시지
    MESSAGE = "지금 현상황 간단하게 보고하고, 앞으로 뭐할지 알려줘"

    print(f"[{time.strftime('%H:%M:%S')}] Claude 자동화 시작...")

    try:
        # 1. Claude 실행 (spawn)
        # encoding='utf-8'을 주어 한글이 깨지지 않게 합니다.
        child = pexpect.spawn(COMMAND, encoding='utf-8', timeout=120)

        # 터미널에 출력되는 내용을 보기 위해 설정 (로그파일로 저장하려면 파일객체 사용)
        child.logfile = sys.stdout

        # 2. 프로그램이 로드될 때까지 잠시 대기 (3초)
        time.sleep(3)

        # 3. /resume 명령어 입력 및 엔터
        print(f"\n[{time.strftime('%H:%M:%S')}] /resume 입력")
        child.sendline("/resume")

        # 4. 대화 목록이 로드될 때까지 대기 (5초 정도 여유를 둠)
        # 네트워크 상황에 따라 시간을 늘리세요.
        time.sleep(5)

        # 5. 맨 위 대화방 선택을 위해 엔터 입력
        print(f"\n[{time.strftime('%H:%M:%S')}] 맨 위 대화방 선택 (Enter)")
        child.sendline()  # 엔터 키 역할

        # 6. 이전 대화 내역을 불러오는 시간 대기 (상황에 따라 5~10초)
        time.sleep(10)

        # 7. 메시지 전송
        print(f"\n[{time.strftime('%H:%M:%S')}] 메시지 전송: {MESSAGE}")
        child.sendline(MESSAGE)

        # 8. 답변이 생성될 때까지 기다림 (세션 유지를 위해)
        # 답변이 길 수 있으므로 60초 이상 대기하거나, 프로세스가 끝날 때까지 기다리게 할 수 있습니다.
        print(f"\n[{time.strftime('%H:%M:%S')}] 답변 생성 대기 중...")
        time.sleep(60)

        # 9. 종료 (/exit 명령어로 깔끔하게 종료)
        child.sendline("/exit")
        time.sleep(2)
        child.close()

        print(f"\n[{time.strftime('%H:%M:%S')}] 작업 완료.")

    except Exception as e:
        print(f"\n[오류 발생] {e}")


if __name__ == "__main__":
    run_claude_automation()