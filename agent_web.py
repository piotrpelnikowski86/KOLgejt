import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO
import warnings

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="📈", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- LISTY ZAPASOWE (TOP 50) ---
# Używane do Podglądu Live oraz jako Koło Ratunkowe, gdyby pełne skanowanie padło.
SP500_TOP50 = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO",
    "JPM", "V", "XOM", "UNH", "MA", "PG", "JNJ", "HD", "MRK", "COST",
    "ABBV", "CVX", "CRM", "BAC", "WMT", "AMD", "ACN", "PEP", "KO", "LIN",
    "TMO", "DIS", "MCD", "CSCO", "ABT", "INTC", "WFC", "VZ", "NFLX", "QCOM",
    "INTU", "NKE", "IBM", "PM", "GE", "AMAT", "TXN", "NOW", "SPGI", "CAT"
]

NASDAQ_TOP50 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP",
    "AMD", "NFLX", "CSCO", "INTC", "TMUS", "CMCSA", "TXN", "AMAT", "QCOM", "HON",
    "INTU", "AMGN", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADP", "LRCX", "ADI",
    "REGN", "VRTX", "MU", "PANW", "SNPS", "KLAC", "CDNS", "CHTR", "MELI", "MAR",
    "CSX", "PYPL", "MNST", "ORLY", "ASML", "NXPI", "CTAS", "WDAY", "FTNT", "KDP"
]

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

# --- INTELIGENTNE POBIERANIE LISTY (FULL SCAN) ---

@st.cache_data(ttl=3600) # Cache na 1h
def get_tickers_full(market_type):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    # 1. NASDAQ (Pełna lista)
    if market_type == "Nasdaq":
        try:
            # Próba 1: Wikipedia
            url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
            response = requests.get(url, headers=headers)
            tables = pd.read_html(StringIO(response.text))
            for t in tables:
                if 'Ticker' in t.columns:
                    return [str(x).replace('.', '-') for x in t['Ticker'].tolist()]
            return [str(x).replace('.', '-') for x in tables[4]['Ticker'].tolist()]
        except:
            # Backup: Zwracamy Top 50 (żeby skaner działał mimo błędu sieci)
            return NASDAQ_TOP50

    # 2. S&P 500 (Pełna lista)
    else:
        try:
            # Próba 1: Wikipedia
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            response = requests.get(url, headers=headers)
            tables = pd.read_html(StringIO(response.text))
            return [str(t).replace('.', '-') for t in tables[0]['Symbol'].tolist()]
        except:
            try:
                # Próba 2: GitHub CSV
                url_csv = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
                return [str(t).replace('.', '-') for t in pd.read_csv(url_csv)['Symbol'].tolist()]
            except:
                # Backup: Top 50
                return SP500_TOP50

# --- ANALIZA ---

def analyze_stock(ticker, strategy, params):
    try:
        # Timeout 2s dla szybkości przy pełnym skanowaniu
        data = yf.download(ticker, period="1y", progress=False, timeout=2, auto_adjust=False)
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
            
            if curr_price <= low.iloc[-1] * 1.05:
                result = {
                    "info": "Przy dolnej wstędze",
                    "val": round(low.iloc[-1], 2),
                    "name": "Dolna Band"
                }
                chart_lines = {'Low': low, 'Up': up}

        if result:
            return {
                "ticker": ticker,
                "price": round(close.iloc[-1], 2),
                "change": round(((close.iloc[-1] - close.iloc[-2])/close.iloc[-2])*100, 2),
                "details": result,
                "chart_data": data[['Close']].copy(),
                "extra_lines": chart_lines
            }
    except:
        return None
    return None

# --- INTERFEJS ---

st.title("📈 KOLgejt")

# PANEL BOCZNY (USTAWIENIA)
with st.sidebar:
    st.header("⚙️ Konfiguracja")
    
    st.subheader("1. Rynek")
    market = st.radio("Indeks:", ["🇺🇸 S&P 500", "💻 Nasdaq 100"])
    
    st.divider()
    
    st.subheader("2. Kryteria")
    strat = st.selectbox("Strategia:", ["RSI (Wyprzedanie)", "SMA (Trend)", "Bollinger (Dołki)"])
    
    params = {}
    if "RSI" in strat:
        params['rsi_threshold'] = st.slider("Szukaj RSI poniżej:", 20, 75, 40)
        st.caption("Im wyżej, tym więcej wyników.")
    elif "SMA" in strat:
        params['sma_period'] = st.slider("Długość średniej:", 10, 200, 50)
    elif "Bollinger" in strat:
        st.info("Szukamy ceny przy dolnej wstędze.")

# GŁÓWNY WIDOK

# Ustalenie listy preview (zawsze top 8)
if "Nasdaq" in market:
    preview_tickers = NASDAQ_TOP50[:8]
    market_name = "Nasdaq 100"
else:
    preview_tickers = SP500_TOP50[:8]
    market_name = "S&P 500"

# --- SEKCJA PODGLĄDU (LIVE) ---
st.subheader(f"🔥 Podgląd rynku: {market_name}")
try:
    cols = st.columns(4)
    data_top = yf.download(preview_tickers, period="2d", progress=False, timeout=2, auto_adjust=False)['Close']
    
    for i, t in enumerate(preview_tickers):
        if t in data_top.columns:
            curr = data_top[t].iloc[-1]
            prev = data_top[t].iloc[-2]
            chg = ((curr - prev) / prev) * 100
            
            color = "normal"
            if chg > 0: color = "off" # Streamlit metric sam koloruje na zielono/czerwono
            
            with cols[i % 4]:
                st.metric(t, f"{curr:.2f}$", f"{chg:.2f}%")
except:
    st.caption("Ładowanie podglądu...")

st.divider()

# --- SEKCJA SKANERA ---
st.subheader("📡 Pełny Skaner")

if st.button(f"🔍 SKANUJ CAŁY {market_name.upper()}", type="primary", use_container_width=True):
    
    # 1. Pobieranie pełnej listy
    with st.spinner(f"Pobieram pełną listę spółek dla {market_name}..."):
        tickers = get_tickers_full("Nasdaq" if "Nasdaq" in market else "SP500")
    
    # Sprawdzenie czy pobrało full czy backup
    if len(tickers) > 60:
        st.toast(f"Pełny skan: {len(tickers)} spółek.")
    else:
        st.warning(f"⚠️ Tryb awaryjny: Skanuję Top {len(tickers)} (Wikipedia zablokowana).")

    progress = st.progress(0)
    status = st.empty()
    found = []
    
    # Pętla skanowania
    for i, t in enumerate(tickers):
        # Aktualizacja UI co 3% postępu (żeby nie zamulać przeglądarki przy 500 elementach)
        if i % 15 == 0 or i == len(tickers)-1:
            progress.progress((i+1)/len(tickers))
            status.text(f"Analizuję {i+1}/{len(tickers)}: {t}")
        
        res = analyze_stock(t, strat.split()[0], params)
        if res: found.append(res)
    
    progress.empty()
    status.empty()
    
    # WYNIKI
    if found:
        st.success(f"Znaleziono {len(found)} spółek spełniających kryteria!")
        for item in found:
            with st.expander(f"{item['ticker']} ({item['change']}%) - {item['price']}$", expanded=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.write(f"**Sygnał:** {item['details']['info']}")
                    st.metric(item['details']['name'], item['details']['val'])
                    st.link_button("Yahoo Finance", f"https://finance.yahoo.com/quote/{item['ticker']}")
                with c2:
                    chart = item['chart_data'].tail(60)
                    for k, v in item['extra_lines'].items():
                        chart[k] = v
                    st.line_chart(chart)
    else:
        st.warning("Brak wyników.")
        st.info("Rynek nie daje okazji przy tych ustawieniach. Spróbuj poluzować kryteria w panelu bocznym.")
