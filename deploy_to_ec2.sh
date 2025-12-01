#!/bin/bash
# EC2 NOTAM 크롤러 배포 스크립트

EC2_IP="3.27.240.67"
EC2_USER="ubuntu"
KEY_FILE="notam-crawler-key.pem"

echo "======================================"
echo "EC2 NOTAM 크롤러 배포"
echo "======================================"
echo ""

# EC2가 준비될 때까지 대기
echo "⏳ EC2 SSH 준비 대기 중..."
sleep 30

# 1. Python 환경 설정
echo ""
echo "[1/5] Python 환경 설정..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << 'EOF'
sudo apt-get update -qq
sudo apt-get install -y python3-pip > /dev/null 2>&1
pip3 install boto3 requests --quiet
echo "✅ Python 환경 설정 완료"
EOF

# 2. 크롤러 코드 업로드
echo ""
echo "[2/5] 크롤러 코드 업로드..."
scp -i "$KEY_FILE" -o StrictHostKeyChecking=no ec2_notam_crawler.py "$EC2_USER@$EC2_IP:/home/ubuntu/"
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_IP" "chmod +x /home/ubuntu/ec2_notam_crawler.py"
echo "✅ 크롤러 코드 업로드 완료"

# 3. cron 설정 (5분마다)
echo ""
echo "[3/5] cron 설정 (5분마다)..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_IP" << 'EOF'
(crontab -l 2>/dev/null | grep -v ec2_notam_crawler.py; echo "*/5 * * * * /usr/bin/python3 /home/ubuntu/ec2_notam_crawler.py >> /home/ubuntu/crawler.log 2>&1") | crontab -
echo "✅ cron 설정 완료"
EOF

# 4. 첫 실행 테스트
echo ""
echo "[4/5] 첫 실행 테스트..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_IP" "python3 /home/ubuntu/ec2_notam_crawler.py"

# 5. 로그 확인
echo ""
echo "[5/5] 로그 확인..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_IP" "tail -20 /home/ubuntu/crawler.log"

echo ""
echo "======================================"
echo "✅ EC2 배포 완료!"
echo "======================================"
echo ""
echo "📊 모니터링 명령어:"
echo "  - 로그 확인: ssh -i $KEY_FILE $EC2_USER@$EC2_IP 'tail -f /home/ubuntu/crawler.log'"
echo "  - cron 확인: ssh -i $KEY_FILE $EC2_USER@$EC2_IP 'crontab -l'"
echo "  - 수동 실행: ssh -i $KEY_FILE $EC2_USER@$EC2_IP 'python3 /home/ubuntu/ec2_notam_crawler.py'"
echo ""
