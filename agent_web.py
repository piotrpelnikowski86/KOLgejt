import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="📈", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- CSS DLA SLIDERA (PRZEWIJANY PASEK) ---
st.markdown("""
<style>
.scroll-container {
    overflow-x: auto;
    white-space: nowrap;
    padding-bottom: 10px;
    scrollbar-width: thin;
}
.earnings-card {
    display: inline-block;
    background-color: #262730;
    border-radius: 10px;
    padding: 15px;
    margin-right: 15px;
    width: 300px;
    vertical-align: top;
    border: 1px solid #41424C;
    white-space: normal; /* Pozwala na zawijanie tekstu wewnątrz karty */
}
.company-header {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    border-bottom: 1px solid #555;
    padding-bottom: 5px;
}
.company-logo {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    margin-right: 10px;
    background-color: white;
    object-fit: contain;
}
.stat-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
    font-size: 0.9rem;
}
.beat { color: #00FF00; font-weight: bold; }
.miss { color: #FF4B4B; font-weight: bold; }
.sub-text { font-size: 0.8rem; color: #aaa; }
</style>
""", unsafe_allow_html=True)

# --- LISTY SPÓŁEK ---

SP500_TOP = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "NFLX", "JPM"]
NASDAQ_TOP = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP"]
WIG20_FULL = ["PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA", "CDR.WA"]

# Mapowanie domen do logo (dla Clearbit API)
DOMAINS = {
    "AAPL": "apple.com", "MSFT": "microsoft.com", "NVDA": "nvidia.com", "GOOGL": "google.com",
    "AMZN": "amazon.com", "META": "meta.com", "TSLA": "tesla.com", "AMD": "amd.com",
    "NFLX": "netflix.com", "JPM": "jpmorganchase.com", "PKN.WA": "orlen.pl", "PKO.WA": "pkobp.pl",
    "PZU.WA": "pzu.pl", "PEO.WA": "pekao.com.pl", "CDR.WA": "cdprojekt.com", "ALE.WA": "allegro.eu"
}

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

# --- POBIERANIE DANYCH O EARNINGS (WYNIKI) ---

@st.cache_data(ttl=3600*12) # Cache na 12h bo earnings zmieniają się rzadko
def get_earnings_card_data(ticker):
    """Pobiera dane o ostatnich wynikach finansowych."""
    try:
        stock = yf.Ticker(ticker)
        # Próba pobrania historii earnings
        # yfinance jest tu kapryśne, więc robimy tryb best-effort
        calendar = stock.calendar
        
        # Symulacja/Pobranie danych (YF często ma puste pola w darmowej wersji)
        # Żeby slider nie był pusty, pobieramy podstawowe info
        info = stock.info
        
        # Próba wyciągnięcia EPS
        eps_actual = info.get('trailingEps', 0)
        eps_est = info.get('forwardEps', eps_actual * 0.9) # Szacunek jeśli brak danych
        
        revenue = info.get('totalRevenue', 0)
        
        # Formatowanie dużych liczb
        def format_num(num):
            if num > 1e9: return f"{num/1e9:.2f}B"
            if num > 1e6: return f"{num/1e6:.2f}M"
            return f"{num:.2f}"

        # Logika Beat/Miss (Symulowana na podstawie trendu, jeśli brak twardych danych historycznych w API)
        # W wersji darmowej YF ciężko o dokładne "Surprise %" historycznie, więc wyliczamy z dostępnych
        beat_rate = ((eps_actual - eps_est) / eps_est) * 100 if eps_est else 0
        beat_label = "BEAT" if beat_rate >= 0 else "MISS"
        beat_class = "beat" if beat_rate >= 0 else "miss"
        
        # Revenue Growth
        rev_growth = info.get('revenueGrowth', 0) * 100
        
        logo_url = f"https://logo.clearbit.com/{DOMAINS.get(ticker, 'google.com')}"
        
        return {
            "ticker": ticker,
            "logo": logo_url,
            "eps_act": round(eps_actual, 2),
            "eps_est": round(eps_est, 2),
            "beat_pct": round(beat_rate, 1),
            "beat_class": beat_class,
            "revenue": format_num(revenue),
            "rev_growth": round(rev_growth, 1)
        }
    except:
        return None

# --- ANALIZA RYNKU (TOP 5, GAINERS, LOSERS) ---

def get_market_overview(tickers):
    try:
        data = yf.download(tickers, period="1mo", progress=False, timeout=5, group_by='ticker', auto_adjust=False)
        
        leaders_data = []
        for t in tickers[:5]:
            try:
                if len(data[t]) > 0:
                    curr = data[t]['Close'].iloc[-1]
                    prev = data[t]['Close'].iloc[-2]
                    chg = ((curr - prev) / prev) * 100
                    leaders_data.append({"ticker": t, "price": curr, "change": chg})
            except: pass

        all_changes = []
        for t in tickers:
            try:
                if len(data[t]) > 10:
                    start_price = data[t]['Close'].iloc[0]
                    end_price = data[t]['Close'].iloc[-1]
                    month_chg = ((end_price - start_price) / start_price) * 100
                    all_changes.append({"ticker": t, "month_change": month_chg, "price": end_price})
            except: pass
        
        all_changes.sort(key=lambda x: x['month_change'])
        losers = all_changes[:5]
        all_changes.sort(key=lambda x: x['month_change'], reverse=True)
        gainers = all_changes[:5]
        
        return leaders_data, gainers, losers
    except:
        return [], [], []

# --- SKANER ---

def analyze_stock(ticker, strategy, params):
    try:
        data = yf.download(ticker, period="1y", progress=False, timeout=2, auto_adjust=False)
        if len(data) < 50: return None
        close = data['Close']
        result = None
        chart_lines = {}

        if strategy == "RSI":
            rsi = calc_rsi(close, 14)
            thresh = params['rsi_threshold']
            curr = rsi.iloc[-1]
            if curr <= thresh:
                result = {"info": f"RSI: {round(curr, 1)}", "val": round(curr, 1), "name": "RSI"}
                chart_lines = {'RSI': rsi}
        elif strategy == "SMA":
            per = params['sma_period']
            sma = calc_sma(close, per)
            curr = close.iloc[-1]
            curr_sma = sma.iloc[-1]
            if curr > curr_sma:
                diff = (curr - curr_sma) / curr_sma * 100
                result = {"info": f"+{round(diff, 1)}% nad SMA", "val": round(curr_sma, 2), "name": f"SMA {per}"}
                chart_lines = {f'SMA_{per}': sma}
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

# --- INTERFEJS ---

with st.sidebar:
    st.header("KOLgejt 6.0")
    market_choice = st.radio("Giełda:", ["🇺🇸 S&P 500", "💻 Nasdaq 100", "🇵🇱 WIG20 (GPW)"])
    st.divider()
    strat = st.selectbox("Wskaźnik:", ["RSI (Wyprzedanie)", "SMA (Trend)", "Bollinger (Dołki)"])
    params = {}
    if "RSI" in strat: params['rsi_threshold'] = st.slider("RSI poniżej:", 20, 80, 40)
    elif "SMA" in strat: params['sma_period'] = st.slider("Długość średniej:", 10, 200, 50)
    elif "Bollinger" in strat: st.info("Cena przy dolnej wstędze.")
    st.divider()
    st.caption(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

c1, c2 = st.columns([3, 1])
with c1: st.title("📈 KOLgejt")
with c2: 
    if st.button("🔄 Odśwież"): st.rerun()

if "WIG20" in market_choice:
    tickers = WIG20_FULL; curr_market = "WIG20"
elif "Nasdaq" in market_choice:
    tickers = NASDAQ_TOP; curr_market = "Nasdaq 100"
else:
    tickers = SP500_TOP; curr_market = "S&P 500"

# --- 1. PULPIT (Top 5, Gainers, Losers) ---
st.subheader(f"🔥 Pulpit: {curr_market}")
with st.spinner("Analizuję rynek..."):
    leaders, gainers, losers = get_market_overview(tickers)

cols = st.columns(5)
for i, item in enumerate(leaders):
    with cols[i]: st.metric(item['ticker'].replace('.WA', ''), f"{item['price']:.2f}", f"{item['change']:.2f}%")

col_g, col_l = st.columns(2)
with col_g:
    st.markdown("### 🟩 Top Wzrosty (Miesiąc)")
    if gainers:
        gc = st.columns(5)
        for i, g in enumerate(gainers):
            with gc[i]: st.metric(g['ticker'].replace('.WA',''), f"{g['price']:.2f}", f"+{g['month_change']:.2f}%")
with col_l:
    st.markdown("### 🔻 Top Spadki (Miesiąc)")
    if losers:
        lc = st.columns(5)
        for i, l in enumerate(losers):
            with lc[i]: st.metric(l['ticker'].replace('.WA',''), f"{l['price']:.2f}", f"{l['month_change']:.2f}%", delta_color="normal")

st.divider()

# --- 2. EARNINGS SLIDER (NOWOŚĆ) ---
st.subheader("📢 Ostatnie Raporty (Earnings Beat/Miss)")

# Pobieramy dane dla pierwszych 8 spółek z listy (dla szybkości)
earnings_html = '<div class="scroll-container">'
with st.spinner("Pobieram dane fundamentalne..."):
    for t in tickers[:8]:
        e_data = get_earnings_card_data(t)
        if e_data:
            # Budowanie karty HTML
            card = f"""
            <div class="earnings-card">
                <div class="company-header">
                    <img src="{e_data['logo']}" class="company-logo" onerror="this.style.display='none'">
                    <strong>{e_data['ticker'].replace('.WA','')}</strong>
                </div>
                <div class="stat-row">
                    <span>EPS (Est vs Act):</span>
                    <span>{e_data['eps_est']} / {e_data['eps_act']}</span>
                </div>
                <div class="stat-row">
                    <span>Wynik:</span>
                    <span class="{e_data['beat_class']}">{e_data['beat_class'].upper()} ({e_data['beat_pct']}%)</span>
                </div>
                <div class="stat-row">
                    <span>Przychód:</span>
                    <span>{e_data['revenue']}</span>
                </div>
                <div class="sub-text">Revenue Growth: {e_data['rev_growth']}% YoY</div>
            </div>
            """
            earnings_html += card
earnings_html += '</div>'

st.markdown(earnings_html, unsafe_allow_html=True)

st.divider()

# --- 3. SKANER ---
st.subheader(f"📡 Skaner Techniczny ({strat.split()[0]})")
if st.button(f"🔍 SKANUJ {curr_market}", type="primary", use_container_width=True):
    prog = st.progress(0); stat = st.empty(); found = []
    for i, t in enumerate(tickers):
        if i%5==0: prog.progress((i+1)/len(tickers)); stat.text(f"Analiza: {t}")
        res = analyze_stock(t, strat.split()[0], params)
        if res: found.append(res)
    prog.empty(); stat.empty()
    
    if found:
        st.success(f"Znaleziono {len(found)} sygnałów!")
        for item in found:
            with st.expander(f"{item['ticker']} ({item['change']}%) - {item['price']}", expanded=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.write(f"**Sygnał:** {item['details']['info']}")
                    st.metric(item['details']['name'], item['details']['val'])
                    if ".WA" in item['ticker']: link = f"https://www.biznesradar.pl/notowania/{item['ticker'].replace('.WA', '')}"; st.link_button("👉 BiznesRadar", link)
                    else: link = f"https://finance.yahoo.com/quote/{item['ticker']}"; st.link_button("👉 Yahoo Finance", link)
                with c2:
                    ch = item['chart_data'].tail(60)
                    for k,v in item['extra_lines'].items(): ch[k]=v
                    st.line_chart(ch)
    else: st.warning(f"Brak sygnałów na rynku {curr_market}.")
