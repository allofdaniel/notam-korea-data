#!/bin/bash
# NOTAM 크롤러 자동 실행 설정

echo "NOTAM 크롤러 cron 설정 시작..."

# crontab에 추가할 작업들
# 1. 5분마다 최근 NOTAM 수집
# 2. 매일 자정에 하루치 NOTAM 전체 수집

# 현재 crontab 백업
crontab -l > /tmp/current_crontab 2>/dev/null || touch /tmp/current_crontab

# NOTAM 크롤러 작업 추가
cat >> /tmp/current_crontab << 'CRON'
# NOTAM 실시간 모니터링 - 5분마다
*/5 * * * * cd /home/ubuntu && python3 notam_hybrid_crawler.py >> notam_crawler.log 2>&1

# NOTAM 일일 전체 동기화 - 매일 자정
0 0 * * * cd /home/ubuntu && python3 notam_hybrid_crawler.py >> notam_daily_sync.log 2>&1
CRON

# 새 crontab 적용
crontab /tmp/current_crontab

echo "✅ cron 설정 완료!"
echo ""
echo "설정된 작업:"
crontab -l | grep notam

echo ""
echo "즉시 첫 수집 시작..."
cd /home/ubuntu && python3 notam_hybrid_crawler.py
