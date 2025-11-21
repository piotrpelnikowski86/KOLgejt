import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="📈", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- LISTY SPÓŁEK (STABILNE) ---

# USA - S&P 500 (Top 50)
SP500_TOP = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO",
    "JPM", "V", "XOM", "UNH", "MA", "PG", "JNJ", "HD", "MRK", "COST",
    "ABBV", "CVX", "CRM", "BAC", "WMT", "AMD", "ACN", "PEP", "KO", "LIN",
    "TMO", "DIS", "MCD", "CSCO", "ABT", "INTC", "WFC", "VZ", "NFLX", "QCOM",
    "INTU", "NKE", "IBM", "PM", "GE", "AMAT", "TXN", "NOW", "SPGI", "CAT"
]

# USA - Nasdaq 100 (Top 50)
NASDAQ_TOP = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP",
    "AMD", "NFLX", "CSCO", "INTC", "TMUS", "CMCSA", "TXN", "AMAT", "QCOM", "HON",
    "INTU", "AMGN", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADP", "LRCX", "ADI",
    "REGN", "VRTX", "MU", "PANW", "SNPS", "KLAC", "CDNS", "CHTR", "MELI", "MAR",
    "CSX", "PYPL", "MNST", "ORLY", "ASML", "NXPI", "CTAS", "WDAY", "FTNT", "KDP"
]

# POLSKA - WIG20 (Pełna lista)
WIG20_FULL = [
    "PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA",
    "CDR.WA", "SPL.WA", "CPS.WA", "PGE.WA", "KRU.WA", "KTY.WA", "ACP.WA", "MBK.WA",
    "JSW.WA", "ALR.WA", "TPE.WA", "PCO.WA"
]

# --- FUNKCJE POMOCNICZE ---

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

# --- ANALIZA RYNKU (TOP 5 & SPADKI) ---

def get_market_overview(tickers):
    """Pobiera dane dla Top 5 i oblicza spadki miesięczne dla całej listy."""
    try:
        # Pobieramy dane z ostatniego miesiąca dla CAŁEJ listy (dla efektywności)
        # group_by='ticker' pozwala łatwiej operować na kolumnach
        data = yf.download(tickers, period="1mo", progress=False, timeout=5, group_by='ticker', auto_adjust=False)
        
        # 1. Top 5 (Ceny bieżące)
        top5_data = []
        # Bierzemy po prostu 5 pierwszych z listy (które są zazwyczaj największe)
        for t in tickers[:5]:
            try:
                if len(data[t]) > 0:
                    curr = data[t]['Close'].iloc[-1]
                    prev = data[t]['Close'].iloc[-2]
                    chg = ((curr - prev) / prev) * 100
                    top5_data.append({"ticker": t, "price": curr, "change": chg})
            except: pass

        # 2. Największe spadki (30 dni)
        losers = []
        for t in tickers:
            try:
                # Obliczamy zmianę od początku miesiąca do teraz
                if len(data[t]) > 10: # Musi być trochę danych
                    start_price = data[t]['Close'].iloc[0]
                    end_price = data[t]['Close'].iloc[-1]
                    month_chg = ((end_price - start_price) / start_price) * 100
                    
                    if month_chg < 0: # Tylko spadkowe
                        losers.append({"ticker": t, "month_change": month_chg, "price": end_price})
            except: pass
        
        # Sortujemy spadki (od największego minusa)
        losers.sort(key=lambda x: x['month_change'])
        
        return top5_data, losers[:5] # Zwracamy Top 5 i 5 największych spadkowiczów
    except Exception as e:
        return [], []

# --- ANALIZA TECHNICZNA (SKANER) ---

def analyze_stock(ticker, strategy, params):
    try:
        data = yf.download(ticker, period="1y", progress=False, timeout=2, auto_adjust=False)
        if len(data) < 50: return None

        close = data['Close']
        result = None
        chart_lines = {}

        # RSI
        if strategy == "RSI":
            rsi = calc_rsi(close, 14)
            thresh = params['rsi_threshold']
            curr = rsi.iloc[-1]
            if curr <= thresh:
                result = {"info": f"RSI: {round(curr, 1)}", "val": round(curr, 1), "name": "RSI"}
                chart_lines = {'RSI': rsi}

        # SMA
        elif strategy == "SMA":
            per = params['sma_period']
            sma = calc_sma(close, per)
            curr = close.iloc[-1]
            curr_sma = sma.iloc[-1]
            if curr > curr_sma:
                diff = (curr - curr_sma) / curr_sma * 100
                result = {"info": f"+{round(diff, 1)}% nad SMA", "val": round(curr_sma, 2), "name": f"SMA {per}"}
                chart_lines = {f'SMA_{per}': sma}

        # BOLLINGER
        elif strategy == "Bollinger":
            up, low = calc_bollinger(close, 20, 2)
            curr = close.iloc[-1]
            curr_low = low.iloc[-1]
            if curr <= curr_low * 1.05:
                result = {"info": "Przy dolnej wstędze", "val": round(curr_low, 2), "name": "Dolna Band"}
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

# --- INTERFEJS APLIKACJI ---

# Pasek boczny
with st.sidebar:
    st.header("KOLgejt 5.0")
    
    st.subheader("1. Wybór Rynku")
    market_choice = st.radio("Giełda:", ["🇺🇸 S&P 500", "💻 Nasdaq 100", "🇵🇱 WIG20 (GPW)"])
    
    st.divider()
    
    st.subheader("2. Kryteria Skanera")
    strat = st.selectbox("Wskaźnik:", ["RSI (Wyprzedanie)", "SMA (Trend)", "Bollinger (Dołki)"])
    
    params = {}
    if "RSI" in strat:
        params['rsi_threshold'] = st.slider("RSI poniżej:", 20, 80, 40)
    elif "SMA" in strat:
        params['sma_period'] = st.slider("Długość średniej:", 10, 200, 50)
    elif "Bollinger" in strat:
        st.info("Cena przy dolnej wstędze.")
        
    st.divider()
    st.caption(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# GŁÓWNY EKRAN
c1, c2 = st.columns([3, 1])
with c1:
    st.title("📈 KOLgejt")
with c2:
    if st.button("🔄 Odśwież dane"):
        st.rerun()

# Dobór listy spółek
if "WIG20" in market_choice:
    tickers = WIG20_FULL
    curr_market = "WIG20"
elif "Nasdaq" in market_choice:
    tickers = NASDAQ_TOP50
    curr_market = "Nasdaq 100"
else:
    tickers = SP500_TOP
    curr_market = "S&P 500"

# --- SEKCJA 1: PULPIT (Top 5 + Spadki) ---

st.subheader(f"🔥 Pulpit Rynku: {curr_market}")

# Pobieramy dane do pulpitu (Top 5 i Losers)
with st.spinner("Pobieram dane rynkowe..."):
    top5, month_losers = get_market_overview(tickers)

# Wyświetlenie TOP 5
cols = st.columns(5)
for i, item in enumerate(top5):
    with cols[i]:
        color = "normal"
        if item['change'] > 0: color = "off" # Streamlit auto-colors positive green
        st.metric(item['ticker'].replace('.WA', ''), f"{item['price']:.2f}", f"{item['change']:.2f}%")

st.write("")

# Wyświetlenie SPADKOWICZÓW (Miesiąc)
with st.expander("🔻 Największe spadki (Ostatnie 30 dni) - Zobacz listę", expanded=True):
    if month_losers:
        l_cols = st.columns(5)
        for i, loser in enumerate(month_losers):
            with l_cols[i]:
                st.metric(
                    loser['ticker'].replace('.WA', ''), 
                    f"{loser['price']:.2f}", 
                    f"{loser['month_change']:.2f}%",
                    delta_color="inverse" # Czerwony kolor dla minusa
                )
    else:
        st.write("Brak danych lub wszystkie spółki rosną.")

st.divider()

# --- SEKCJA 2: SKANER ---
st.subheader(f"📡 Skaner Techniczny ({strat.split()[0]})")

if st.button(f"🔍 SKANUJ {curr_market}", type="primary", use_container_width=True):
    
    progress = st.progress(0)
    status = st.empty()
    found = []
    
    for i, t in enumerate(tickers):
        if i % 5 == 0: 
            progress.progress((i+1)/len(tickers))
            status.text(f"Analiza: {t}")
        
        res = analyze_stock(t, strat.split()[0], params)
        if res: found.append(res)
    
    progress.empty()
    status.empty()
    
    if found:
        st.success(f"Znaleziono {len(found)} sygnałów!")
        for item in found:
            with st.expander(f"{item['ticker']} ({item['change']}%) - {item['price']}", expanded=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.write(f"**Sygnał:** {item['details']['info']}")
                    st.metric(item['details']['name'], item['details']['val'])
                    
                    # Linkowanie: Yahoo dla USA, Bankier/BiznesRadar dla PL (opcjonalnie)
                    if ".WA" in item['ticker']:
                        link = f"https://www.biznesradar.pl/notowania/{item['ticker'].replace('.WA', '')}"
                        st.link_button("👉 BiznesRadar (PL)", link)
                    else:
                        link = f"https://finance.yahoo.com/quote/{item['ticker']}"
                        st.link_button("👉 Yahoo Finance", link)

                with c2:
                    chart = item['chart_data'].tail(60)
                    for k, v in item['extra_lines'].items():
                        chart[k] = v
                    st.line_chart(chart)
    else:
        st.warning(f"Brak sygnałów na rynku {curr_market}. Spróbuj zmienić strategię.")
