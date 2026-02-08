import streamlit as st
import ccxt
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------
# [기본 설정]
st.set_page_config(page_title="김프 연구소", page_icon="💰", layout="wide")
st.title("💰실시간 김치프리미엄 감시기")
st.markdown("---")

# ---------------------------------------------------------
# 1. '기억 장치' (세션 스테이트) 초기화
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'rate' not in st.session_state:
    st.session_state.rate = 1465.0

# ---------------------------------------------------------
# 2. 거래소 연결
@st.cache_resource
def get_exchanges():
    return ccxt.upbit(), ccxt.binance()

upbit, binance = get_exchanges()

# ---------------------------------------------------------
# 3. 데이터 가져오기 로직
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
        
        result = []
        for coin in common_coins:
            u_sym = f"{coin}/KRW"
            b_sym = f"{coin}/USDT"
            
            # 한글명
            try:
                korean_name = upbit.market(u_sym)['info']['korean_name']
            except:
                korean_name = coin

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
                        "김프(%)": kimp
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

# [새로고침 버튼]
with col1:
    if st.button('🔄 시세 새로고침', type="primary"):
        with st.spinner('거래소 데이터 긁어오는 중...'):
            new_df, new_rate = load_data()
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

    # ★ [필터링 로직] 검색어가 '있을 때만' 남기고, 없으면 전체 목록 유지
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

    # 색상 (빨강/파랑)
    def color_kimp(val):
        color = 'red' if val > 5 else ('blue' if val < 0 else 'black')
        return f'color: {color}; font-weight: bold'

    # 표 그리기
    display_cols = ["한글명", "코인(심볼)", "한국가격", "해외가격", "차액(Gap)", "김프(%)"]
    st.dataframe(
        display_df[display_cols].style.format(format_dict).map(color_kimp, subset=['김프(%)']),
        use_container_width=True,
        height=800
    )

else:
    st.write("👆 **'시세 새로고침'** 버튼을 눌러주세요!")