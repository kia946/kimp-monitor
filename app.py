import streamlit as st
import ccxt
import pandas as pd
import yfinance as yf
import time  # <--- ★ 이거 꼭 추가해야 합니다! (시계 기능)
import requests  # 이게 없으면 에러 납니다!

# --- 지갑 상태 조회 함수 정의 (이걸 먼저 넣어야 함) ---
def get_upbit_wallet_status():
    url = "https://api.upbit.com/v1/status/wallet"
    try:
        response = requests.get(url, timeout=1) # 1초 안에 답 없으면 패스
        data = response.json()
        
        # 보기 편하게 가공
        wallet_map = {}
        for item in data:
            symbol = item['currency'] # BTC, ETH 등
            state = item['wallet_state'] # working, withdraw_suspended 등
            
            is_warning = False
            desc = "정상"
            
            if state == 'withdraw_suspended':
                desc = "출금중단(주의)"
                is_warning = True
            elif state == 'deposit_suspended':
                desc = "입금중단(주의)"
                is_warning = True
            elif state == 'inactive':
                desc = "입출금중단(위험)"
                is_warning = True
                
            wallet_map[symbol] = {'desc': desc, 'warning': is_warning}
            
        return wallet_map
    except:
        return {} # 에러나면 빈 깡통 리턴
# ---------------------------------------------------------
# [기본 설정]
# [기본 설정]
st.set_page_config(
    page_title="김프 연구소 - 실시간 비트코인 김치프리미엄(Kimchi Premium) 감시기", # 제목을 길고 자세하게!
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/kia946/kimp-monitor',
        'Report a bug': "https://github.com/kia946/kimp-monitor",
        'About': "### 1초마다 갱신되는 실시간 김프 감시기입니다."
    }
)

# ---------------------------------------------------------
# 1. '기억 장치' (세션 스테이트) 초기화
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'rate' not in st.session_state:
    st.session_state.rate = 1465.0

# ---------------------------------------------------------
# 2. 거래소 연결 (한 번만 연결하고 기억함)
@st.cache_resource
def get_exchanges():
    return ccxt.upbit(), ccxt.binanceus()

upbit, binance = get_exchanges()

# ---------------------------------------------------------
# 3. 데이터 가져오기 로직 (수정됨: 지갑 상태 감지 추가)
def load_data():
    try:
        # 환율 가져오기
        try:
            exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except:
            exchange_rate = 1465.0
        
        # 거래소 데이터 가져오기
        upbit.load_markets()
        binance.load_markets()
        
        upbit_tickers = upbit.fetch_tickers()
        binance_tickers = binance.fetch_tickers()

        # 공통 코인 찾기
        upbit_coins = set([x.split('/')[0] for x in upbit_tickers.keys() if '/KRW' in x])
        binance_coins = set([x.split('/')[0] for x in binance_tickers.keys() if '/USDT' in x])
        common_coins = list(upbit_coins & binance_coins)
        
        # === [추가 1] 루프 돌기 전에 지갑 상태 한 번 싹 긁어오기 ===
        wallet_status = get_upbit_wallet_status() 
        # =======================================================
        
        result = []
        for coin in common_coins:
            u_sym = f"{coin}/KRW"
            b_sym = f"{coin}/USDT"
            
            # 한글명
            try:
                korean_name = upbit.market(u_sym)['info']['korean_name']
            except:
                korean_name = coin

            # === [추가 2] 개별 코인 지갑 상태 확인하기 ===
            # 이미 coin 변수에 'BTC', 'ETH' 등이 들어있으므로 바로 조회
            w_info = wallet_status.get(coin, {'desc': '정상', 'warning': False})
            
            # 경고 메시지 처리 (정상이면 빈칸, 문제 있으면 메시지 표시)
            status_msg = w_info['desc'] if w_info['warning'] else "정상"
            # ============================================

            if u_sym in upbit_tickers and b_sym in binance_tickers:
                kp_raw = upbit_tickers[u_sym]['close']
                bp_raw = binance_tickers[b_sym]['close']
                
                if kp_raw and bp_raw and bp_raw > 0:
                    global_price_krw = bp_raw * exchange_rate
                    kimp = ((kp_raw / global_price_krw) - 1) * 100
                    
                    result.append({
                        "코인(심볼)": coin,
                        "한글명": korean_name,
                        "한국_raw": kp_raw,
                        "해외_raw": bp_raw,
                        "김프(%)": kimp,
                        "비고": status_msg  # <--- [추가 3] 표에 보여줄 데이터 추가
                    })
        
        df = pd.DataFrame(result)
        if not df.empty:
            df = df.sort_values(by="김프(%)", ascending=False)
        
        return df, exchange_rate

    except Exception as e:
        st.error(f"데이터 조회 중 에러: {e}")
        return pd.DataFrame(), 1400
# ---------------------------------------------------------
# 4. 화면 구성

col1, col2 = st.columns([1, 4])

# [새로고침 메뉴 구성]
with col1:
    # 1. 수동 버튼
    if st.button('🔄 즉시 새로고침', type="primary"):
        with st.spinner('시세 조회 중...'):
            new_df, new_rate = load_data()
            if not new_df.empty:
                st.session_state.df = new_df
                st.session_state.rate = new_rate
    
    # 2. 자동 새로고침 스위치
    auto_refresh = st.checkbox('⚡ 3초마다 자동 업데이트')

    # 스위치가 켜져 있으면? -> 데이터를 미리 가져옵니다. (화면은 아직 안 그림)
    if auto_refresh:
        new_df, new_rate = load_data()
        if not new_df.empty:
            st.session_state.df = new_df
            st.session_state.rate = new_rate
# [화폐 선택]
with col2:
    currency_mode = st.radio(
        "💱 표시 통화",
        ["KRW (원화)", "USD (달러)"],
        horizontal=True
    )

# ---------------------------------------------------------
# 5. 결과 출력 (데이터가 메모리에 있을 때만)
if not st.session_state.df.empty:
    
    # 환율 정보
    st.info(f"💵 현재 환율: **1달러 = {st.session_state.rate:,.2f}원**")
    
    # ★ [검색 기능]
    search_term = st.text_input("🔍 코인 검색", placeholder="예: 비트코인, BTC, 리플 (지우면 전체 목록)")
    
    # 일단 전체 목록을 가져옴
    display_df = st.session_state.df.copy()

    # ★ [필터링 로직]
    if search_term:
        display_df = display_df[
            display_df['코인(심볼)'].str.contains(search_term, case=False) | 
            display_df['한글명'].str.contains(search_term)
        ]

    st.subheader(f"🔥 김치프리미엄 현황 (총 {len(display_df)}개)")

    # 화폐 단위 변환
    rate = st.session_state.rate
    if currency_mode == "KRW (원화)":
        display_df['한국가격'] = display_df['한국_raw']
        display_df['해외가격'] = display_df['해외_raw'] * rate
        display_df['차액(Gap)'] = display_df['한국가격'] - display_df['해외가격']
        format_dict = {"한국가격": "{:,.0f}원", "해외가격": "{:,.0f}원", "차액(Gap)": "{:+,.0f}원", "김프(%)": "{:.2f}%"}
    else:
        display_df['한국가격'] = display_df['한국_raw'] / rate
        display_df['해외가격'] = display_df['해외_raw']
        display_df['차액(Gap)'] = display_df['한국가격'] - display_df['해외가격']
        format_dict = {"한국가격": "${:,.4f}", "해외가격": "${:,.4f}", "차액(Gap)": "{:+,.4f}", "김프(%)": "{:.2f}%"}

    # 색상
    def color_kimp(val):
        color = 'red' if val > 5 else ('blue' if val < 0 else 'black')
        return f'color: {color}; font-weight: bold'

    # 표 그리기 (여기 '비고' 추가됨!)
    display_cols = ["한글명", "코인(심볼)", "한국가격", "해외가격", "차액(Gap)", "김프(%)", "비고"] 
    
    st.dataframe(
        display_df[display_cols].style.format(format_dict).map(color_kimp, subset=['김프(%)']),
        use_container_width=True,
        height=800
    )

else:
    st.write("👆 **'시세 새로고침'** 버튼을 눌러주세요!")

# ---------------------------------------------------------
# 6. 계산기 (표 아래에 항상 표시)
st.divider()

st.subheader("🧮 테더(USDT) 환전 계산기")
with st.expander("지금 환전하면 얼마 받을까? (클릭)", expanded=True):
    try:
        # 기존에 연결해둔 upbit 변수 재활용 (속도 향상)
        # 단, 가격은 실시간으로 가져옴
        calc_price = upbit.fetch_ticker('USDT/KRW')['close']
        
        invest_krw = st.number_input("투자할 원화(KRW)를 입력하세요", min_value=10000, value=1000000, step=10000)
        
        get_usdt = invest_krw / calc_price
        
        st.write(f"현재 테더(USDT) 가격: **{calc_price:,.0f} 원**")
        st.success(f"💰 **{invest_krw:,.0f} 원**으로 **{get_usdt:,.2f} USDT**를 살 수 있습니다.")
        
        if calc_price > 1450: 
            st.info(f"💡 팁: 현재 환율(약 1450원)보다 비쌀 수 있습니다. 위쪽 표의 '김프(%)'를 꼭 확인하세요!")
        else:
             st.info(f"🔥 팁: 가격이 좋습니다! 위쪽 표에서 역프인지 확인하고 진입하세요.")

    except Exception as e:
        st.error(f"계산기 에러: {e}")

# ---------------------------------------------------------
# [자동 새로고침 엔진] - 맨 마지막에 있어야 함!
if auto_refresh:
    time.sleep(3) # 3초 기다리고
    st.rerun()    # 다시 처음으로!





