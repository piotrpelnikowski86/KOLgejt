import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt 4.3", page_icon="📊", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

# --- FUNKCJE MATEMATYCZNE ---

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_sma(series, period):
    return series.rolling(window=period).mean()

def calc_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    up = sma + (std * std_dev)
    low = sma - (std * std_dev)
    return up, low

# --- LISTA SPÓŁEK (TOP 50 - GWARANCJA DZIAŁANIA) ---
TOP_STOCKS = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO",
    "JPM", "V", "XOM", "UNH", "MA", "PG", "JNJ", "HD", "MRK", "COST",
    "ABBV", "CVX", "CRM", "BAC", "WMT", "AMD", "ACN", "PEP", "KO", "LIN",
    "TMO", "DIS", "MCD", "CSCO", "ABT", "INTC", "WFC", "VZ", "NFLX", "QCOM",
    "INTU", "NKE", "IBM", "PM", "GE", "AMAT", "TXN", "NOW", "SPGI", "CAT"
]

# --- ANALIZA ---

def analyze_stock(ticker, strategy, params):
    try:
        # Pobieranie danych
        data = yf.download(ticker, period="1y", progress=False, timeout=3, auto_adjust=False)
        if len(data) < 50: return None

        close = data['Close']
        result = None
        chart_lines = {}

        # STRATEGIA 1: RSI
        if strategy == "RSI":
            rsi = calc_rsi(close, 14)
            thresh = params['rsi_threshold']
            curr_rsi = rsi.iloc[-1]
            
            if curr_rsi <= thresh:
                result = {
                    "info": f"RSI: {round(curr_rsi, 1)}",
                    "val": round(curr_rsi, 1),
                    "name": "RSI"
                }
                chart_lines = {'RSI': rsi}

        # STRATEGIA 2: SMA
        elif strategy == "SMA":
            per = params['sma_period']
            sma = calc_sma(close, per)
            curr_price = close.iloc[-1]
            curr_sma = sma.iloc[-1]
            
            if curr_price > curr_sma:
                diff = (curr_price - curr_sma) / curr_sma * 100
                result = {
                    "info": f"+{round(diff, 1)}% nad SMA",
                    "val": round(curr_sma, 2),
                    "name": f"SMA {per}"
                }
                chart_lines = {f'SMA_{per}': sma}

        # STRATEGIA 3: BOLLINGER
        elif strategy == "Bollinger":
            up, low = calc_bollinger(close, 20, 2)
            curr_price = close.iloc[-1]
            curr_low = low.iloc[-1]
            
            if curr_price <= curr_low * 1.05:
                result = {
                    "info": "Przy dolnej wstędze",
                    "val": round(curr_low, 2),
                    "name": "Dolna Band"
                }
                chart_lines = {'Low': low, 'Up': up}

        if result:
            return {
                "ticker": ticker,
                "price": round(close.iloc[-1], 2),
                "details": result,
                "chart_data": data[['Close']].copy(),
                "extra_lines": chart_lines
            }
    except:
        return None
    return None

# --- INTERFEJS ---

st.title("📊 KOLgejt 4.3")

with st.sidebar:
    st.header("Ustawienia")
    strat = st.selectbox("Strategia:", ["RSI", "SMA", "Bollinger"])
    
    params = {}
    st.write("---")
    if strat == "RSI":
        params['rsi_threshold'] = st.slider("Próg RSI", 20, 80, 35) 
    elif strat == "SMA":
        params['sma_period'] = st.slider("Średnia (dni)", 10, 200, 50)
    elif strat == "Bollinger":
        st.info("Cena przy dolnej wstędze.")

# START
if st.button("🔍 SKANUJ RYNEK (Top 50)", type="primary", use_container_width=True):
    st.toast(f"Skanuję rynek...")
    
    bar = st.progress(0)
    found = []
    
    for i, t in enumerate(TOP_STOCKS):
        bar.progress((i+1)/len(TOP_STOCKS))
        res = analyze_stock(t, strat, params)
        if res: found.append(res)
    
    bar.empty()
    
    if found:
        st.success(f"Znaleziono: {len(found)} spółek")
