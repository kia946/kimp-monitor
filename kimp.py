import ccxt
import time
import pandas as pd
import yfinance as yf
from datetime import datetime

# 1. 거래소 연결
upbit = ccxt.upbit()
binance = ccxt.binance()

def get_realtime_exchange_rate():
    """야후 파이낸스에서 실시간 원/달러 환율 가져오기"""
    try:
        # KRW=X는 원/달러 환율 티커입니다
        ticker = yf.Ticker("KRW=X")
        # 가장 최신 데이터 1일치를 가져와서 현재가(Close)만 뽑음
        rate = ticker.history(period="1d")['Close'].iloc[-1]
        return rate
    except:
        print("환율 조회 실패! (기본값 1465원으로 대체합니다)")
        return 1465.0

def get_common_coins():
    """업비트(KRW)와 바이낸스(USDT) 양쪽에 다 있는 코인만 자동 추출"""
    print("⏳ 전체 코인 목록 스캔 중... (잠시만 기다려주세요)")
    
    # 마켓 정보 로드 (모든 코인 목록 가져오기)
    upbit.load_markets()
    binance.load_markets()
    
    # 업비트: KRW 마켓에 있는 코인 이름만 추출 (예: BTC, ETH)
    upbit_coins = set([x.split('/')[0] for x in upbit.symbols if '/KRW' in x])
    
    # 바이낸스: USDT 마켓에 있는 코인 이름만 추출
    binance_coins = set([x.split('/')[0] for x in binance.symbols if '/USDT' in x])
    
    # 교집합(Intersection): 둘 다 있는 것만 남김
    common = list(upbit_coins & binance_coins)
    print(f"✅ 스캔 완료! 총 {len(common)}개의 공통 코인을 찾았습니다.")
    return common

def run_scanner():
    # 1. 실시간 환율 가져오기
    exchange_rate = get_realtime_exchange_rate()
    print(f"\n💵 현재 환율: 1달러 = {exchange_rate:,.2f}원 적용")
    
    # 2. 공통 코인 목록 가져오기 (처음 한 번만 실행해도 되지만, 신규 상장 대비 매번 실행)
    # 속도를 위해 코인 목록은 위에서 한 번 구했다고 가정하고 여기선 생략 가능하지만
    # 일단 전체 로직을 위해 포함합니다. (실제 봇에선 캐싱 추천)
    coins = get_common_coins()
    
    # 3. 데이터 수집 (한방에 가져오기 - fetch_tickers 사용)
    # 일일이 하나씩 요청하면 너무 느려서, 전체를 한 번에 가져오는 기술입니다.
    print("🚀 시세 데이터 수집 중...")
    
    try:
        upbit_tickers = upbit.fetch_tickers() # 업비트 전체 시세
        binance_tickers = binance.fetch_tickers() # 바이낸스 전체 시세
    except Exception as e:
        print(f"API 에러 발생: {e}")
        return

    result_list = []

    for coin in coins:
        try:
            # 심볼 정의 (예: BTC/KRW, BTC/USDT)
            upbit_symbol = f"{coin}/KRW"
            binance_symbol = f"{coin}/USDT"
            
            # 데이터가 둘 다 존재할 때만 계산
            if upbit_symbol in upbit_tickers and binance_symbol in binance_tickers:
                krw_price = upbit_tickers[upbit_symbol]['close']
                usd_price = binance_tickers[binance_symbol]['close']
                
                # 김프 계산
                global_price_krw = usd_price * exchange_rate
                kimp = ((krw_price / global_price_krw) - 1) * 100
                
                # 리스트에 추가 (코인이름, 한국가격, 해외가격, 김프)
                result_list.append({
                    '코인': coin,
                    '한국가격(KRW)': krw_price,
                    '해외가격(USD)': usd_price,
                    '김프(%)': round(kimp, 2)
                })
        except:
            pass

    # 4. 판다스(Pandas)로 예쁘게 보여주기
    df = pd.DataFrame(result_list)
    
    # 김프 높은 순서대로 정렬 (내림차순)
    df = df.sort_values(by='김프(%)', ascending=False)
    
    # 상위 10개만 출력 (너무 많으니까)
    print(f"\n📊 [ {datetime.now().strftime('%H:%M:%S')} ] 김치프리미엄 랭킹 TOP 15")
    print("=" * 60)
    # 보기 좋게 출력 옵션 설정
    pd.set_option('display.float_format', '{:,.2f}'.format)
    # 인덱스 숨기고 출력
    print(df.head(15).to_string(index=False)) 
    print("=" * 60)

# 실행
if __name__ == "__main__":
    while True:
        run_scanner()
        print("\n⏳ 10초 뒤 갱신됩니다... (종료하려면 Ctrl+C)")
        time.sleep(10)