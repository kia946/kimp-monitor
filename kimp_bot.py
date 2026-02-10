import requests
import time

# ==========================================
# [설정] 아까 복사한 디스코드 주소를 여기에 넣으세요!
# ==========================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1470642936567042271/auVe4U-IMYN4YjaYOoCBoFs9Qgofg0Y-cvfQNja7drJv5qYv_ZBJtzDPpmp0k4UaVKLh"

# 1. 디스코드 알림 보내는 함수
def send_discord_alert(msg):
    try:
        data = {"content": msg} # 보낼 메시지
        requests.post(DISCORD_WEBHOOK_URL, json=data)
        print(f"[전송완료] {msg}")
    except Exception as e:
        print(f"[전송실패] {e}")

# 2. 업비트 지갑 상태 조회 함수
def get_upbit_wallet_status():
    url = "https://api.upbit.com/v1/status/wallet"
    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        
        wallet_map = {}
        for item in data:
            symbol = item['currency']
            state = item['wallet_state']
            
            # 위험 상태 정의
            if state == 'withdraw_suspended':
                wallet_map[symbol] = "🚨출금중단(가두리)"
            elif state == 'deposit_suspended':
                wallet_map[symbol] = "⚠️입금중단"
            elif state == 'inactive':
                wallet_map[symbol] = "⛔입출금중단"
            # 'working'(정상)인 경우는 굳이 저장 안 해도 됨 (알림 안 보낼 거니까)
            
        return wallet_map # 문제가 있는 코인들만 리턴됨
    except:
        return {}

# ==========================================
# [실행] 메인 루프 (무한 반복)
# ==========================================
print("--- 김프 연구소 감지기 가동 시작 ---")
send_discord_alert("✅ 김프 연구소 알림봇이 시작되었습니다!")

while True:
    # 1. 지갑 상태 확인
    print("\n🔍 지갑 상태 스캔 중...")
    bad_wallets = get_upbit_wallet_status()
    
    # 2. 문제가 있는 코인이 발견되면 알림 발사!
    if bad_wallets:
        message = "**[긴급] 업비트 지갑 상태 변경 감지!**\n"
        
        # 감지된 코인들 리스트업
        for coin, status in bad_wallets.items():
            # 내가 관심 있는 코인만 필터링하려면 여기에 if문 추가 가능
            message += f"- {coin}: {status}\n"
            
        # 디스코드 전송
        send_discord_alert(message)
    else:
        print("특이사항 없음 (모두 정상)")

    # 3. 너무 자주 보내면 디스코드한테 혼나니까 1분(60초) 대기
    # (실제 김프 매매할 때는 이 시간을 10초나 30초로 줄이셔도 됩니다)
    time.sleep(60)
