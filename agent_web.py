import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO
import warnings

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt 4.1", page_icon="⚙️", layout="wide")
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
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, lower

# --- PANCERNE POBIERANIE LISTY SPÓŁEK ---

@st.cache_data(ttl=24*3600)
def get_tickers(market_type):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    tickers = []
    
    # === NASDAQ 100 ===
    if market_type == "Nasdaq":
        try:
            url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
            response = requests.get(url, headers=headers)
            tables = pd.read_html(StringIO(response.text))
            
            # Szukanie właściwej tabeli
            for t in tables:
                if 'Ticker' in t.columns:
                    return [str(x).replace('.', '-') for x in t['Ticker'].tolist()]
            return [str(x).replace('.', '-') for x in tables[4]['Ticker'].tolist()]
        except:
            # Backup manualny dla Nasdaq (bo CSV jest rzadziej aktualizowany)
            return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX", "INTC", "CSCO", "PEP", "AVGO", "ADBE", "QCOM"]
    
    # === S&P 500 (TU BYŁ PROBLEM - TERAZ NAPRAWIONE) ===
    else:
        # 1. Próba z Wikipedii
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            response = requests.get(url, headers=headers)
            tables = pd.read_html(StringIO(response.text))
            tickers = tables[0]['Symbol'].tolist()
            return [str(t).replace('.', '-') for t in tickers]
        except:
            # 2. PRÓBA ZAPASOWA (GITHUB CSV) - TO URATUJE SKANER
            try:
                url_csv = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
                backup_data = pd.read_csv(url_csv)
                tickers = backup_data['Symbol'].tolist()
                return [str(t).replace('.', '-') for t in tickers]
            except:
                # 3. Ostateczność (tylko jeśli wszystko padnie)
                return ["AAPL", "MSFT", "GOOGL", "AMZN"]
            
    return []

# --- ANALIZA ---

def analyze_stock(ticker, strategy, params):
    try:
        # Pobieramy dane (zapas 2 lata dla SMA200)
        data = yf.download(ticker, period="2y", progress=False, timeout=5, auto_adjust=False)
        
        # Jeśli za mało danych, pomiń
        if len(data) < 200: return None

        close = data['Close']
        result = None
        chart_lines = {}

        # STRATEGIA 1: RSI
        if strategy == "RSI":
            rsi_val = calc_rsi(close, 14)
            threshold = params['rsi_threshold']
            cur = rsi_val.iloc[-1]
            
            # Jeśli RSI jest poniżej progu + mały margines
            if cur <= (threshold + 2):
                result = {
                    "info": f"RSI: {round(cur, 1)} (Silne wyprzedanie)",
                    "metric_val": round(cur, 1),
                    "metric_name": "RSI"
                }
                chart_lines = {'RSI': rsi_val}

        # STRATEGIA 2: SMA
        elif strategy == "SMA":
            period = params['sma_period']
            sma = calc_sma(close, period)
            cur_price = close.iloc[-1]
            cur_sma = sma.iloc[-1]
            
            if cur_price > cur_sma:
                dist = (cur_price - cur_sma) / cur_sma * 100
                result = {
                    "info": f"Trend wzrostowy (+{round(dist, 1)}% nad średnią)",
                    "metric_val": round(cur_sma, 2),
                    "metric_name": f"SMA {period}"
                }
                chart_lines = {f'SMA_{period}': sma}

        # STRATEGIA 3: BOLLINGER
        elif strategy == "Bollinger":
            up, low = calc_bollinger(close, 20, 2)
            cur_price = close.iloc[-1]
            cur_low = low.iloc[-1]
            
            if cur_price <= cur_low * 1.03: # 3% tolerancji
                result = {
                    "info": "Cena przy dolnej wstędze",
                    "metric_val": round(cur_low, 2),
                    "metric_name": "Dolna Band"
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

st.title("⚙️ KOLgejt 4.1")

# PANEL BOCZNY
with st.sidebar:
    st.header("🎛️ Konfiguracja")
    
    st.subheader("1. Rynek")
    market = st.radio("Indeks:", ["S&P 500", "Nasdaq"], label_visibility="collapsed")
    
    st.subheader("2. Strategia")
    strategy_type = st.selectbox("Wskaźnik:", ["RSI", "SMA", "Bollinger"])
    
    params = {}
    st.write("---")
    
    if strategy_type == "RSI":
        params['rsi_threshold'] = st.slider("Próg RSI (Max)", 20, 60, 35)
        st.info("Pokazuje spółki z RSI poniżej tej wartości.")
        
    elif strategy_type == "SMA":
        params['sma_period'] = st.slider("Okres średniej", 10, 200, 50, step=10)
        st.info("Pokazuje spółki, których cena jest powyżej tej średniej.")
        
    elif strategy_type ==
    
