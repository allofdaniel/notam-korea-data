#!/bin/bash
# EC2 API 서버 업데이트 스크립트

# LIMIT 500 제거
sed -i 's/LIMIT 500//g' /home/ubuntu/ec2_api_server.py

# API 서버 재시작
pkill -f ec2_api_server.py
sleep 2
cd /home/ubuntu
nohup python3 ec2_api_server.py > api.log 2>&1 &

echo "✅ API 서버 업데이트 및 재시작 완료"
echo "🔍 프로세스 확인:"
ps aux | grep ec2_api_server | grep -v grep
