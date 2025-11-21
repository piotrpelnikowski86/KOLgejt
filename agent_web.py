import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="📈", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- CSS (STYLIZACJA JAK NA ZDJĘCIU) ---
st.markdown("""
<style>
/* Kontener paska przewijania */
.scroll-container {
    overflow-x: auto;
    white-space: nowrap;
    padding: 20px 0;
    scrollbar-width: thin;
}

/* Karta Earnings (Styl Webull) */
.webull-card {
    display: inline-block;
    background-color: #EAEAEA; /* Jasne tło jak na zdjęciu */
    border-radius: 8px;
    width: 380px;
    margin-right: 20px;
    vertical-align: top;
    font-family: 'Arial', sans-serif;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    overflow: hidden;
    border: 1px solid #ccc;
}

/* Nagłówek z nazwą firmy */
.card-header {
    text-align: center;
    padding: 10px;
    background-color: #f0f2f6;
    color: #333;
    font-weight: bold;
    font-size: 16px;
    border-bottom: 1px solid #ddd;
}

/* Tabela wyników */
.webull-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    text-align: center;
}

.webull-table th {
    background-color: #0099FF; /* Niebieski nagłówek */
    color: white;
    padding: 6px;
    font-weight: 600;
}

.webull-table td {
    padding: 8px;
    color: black;
    border-bottom: 1px solid white;
}

/* Fioletowe wiersze */
.row-purple {
    background-color: #E0CEE0; 
}

/* Kolory Beat/Miss */
.text-beat { color: #00AA00; font-weight: bold; }
.text-miss { color: #FF0000; font-weight: bold; }

/* Sekcja Logo */
.logo-section {
    text-align: center;
    padding: 15px;
    background-color: #EAEAEA;
}
.big-logo {
    height: 50px;
    object-fit: contain;
}

/* Statystyki dolne */
.bottom-stats {
    padding: 10px;
    font-size: 11px;
    color: #333;
    background-color: #EAEAEA;
    line-height: 1.6;
    text-align: left;
    padding-left: 20px;
}
.stat-up { color: #00AA00; font-weight: bold; }
.stat-down { color: #FF0000; font-weight: bold; }

</style>
""", unsafe_allow_html=True)

# --- LISTY SPÓŁEK ---

SP500_TOP = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "NFLX", "JPM", "DIS", "V", "MA"]
NASDAQ_TOP = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP", "AMD", "INTC"]
WIG20_FULL = ["PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA", "CDR.WA"]

# Domeny do logo
DOMAINS = {
    "AAPL": "apple.com", "MSFT": "microsoft.com", "NVDA": "nvidia.com", "GOOGL": "google.com",
    "AMZN": "amazon.com", "META": "meta.com", "TSLA": "tesla.com", "AMD": "amd.com",
    "NFLX": "netflix.com", "PKN.WA": "orlen.pl", "PKO.WA": "pkobp.pl", "CDR.WA": "cdprojekt.com"
}

# --- FUNKCJE ---

def format_large_num(num):
    if num is None: return "-"
    if num > 1e9: return f"{num/1e9:.2f}B"
    if num > 1e6: return f"{num/1e6:.2f}M"
    return f"{num:.2f}"

@st.cache_data(ttl=3600*12)
def get_earnings_card_data(ticker):
    """Pobiera dane i formatuje pod kartę ze zdjęcia."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Próba pobrania danych finansowych
        eps_act = info.get('trailingEps', 0)
        # Symulacja oczekiwań (bo YF free rzadko to daje) - zakładamy małe odchylenie
        eps_est = info.get('forwardEps', eps_act * 0.95) 
        
        rev_act = info.get('totalRevenue', 0)
        rev_est = rev_act * 0.98 # Symulacja oczekiwań
        
        # Obliczenia Beat/Miss
        eps_diff = ((eps_act - eps_est) / eps_est) * 100 if eps_est else 0
        rev_diff = ((rev_act - rev_est) / rev_est) * 100 if rev_est else 0
        
        eps_text = f"Beat by {abs(eps_diff):.0f}%" if eps_diff >= 0 else f"Miss by {abs(eps_diff):.0f}%"
        eps_class = "text-beat" if eps_diff >= 0 else "text-miss"
        
        rev_text = f"Beat by {abs(rev_diff):.0f}%" if rev_diff >= 0 else f"Miss by {abs(rev_diff):.0f}%"
        rev_class = "text-beat" if rev_diff >= 0 else "text-miss"
        
        # Growth metrics
        rev_growth = info.get('revenueGrowth', 0) * 100
        earn_growth = info.get('earningsGrowth', 0) * 100
        
        logo = f"https://logo.clearbit.com/{DOMAINS.get(ticker, 'google.com')}"
        
        return {
            "ticker": ticker,
            "logo": logo,
            "eps_est": round(eps_est, 2),
            "eps_act": round(eps_act, 2),
            "eps_res": eps_text,
            "eps_class": eps_class,
            "rev_est": format_large_num(rev_est),
            "rev_act": format_large_num(rev_act),
            "rev_res": rev_text,
            "rev_class": rev_class,
            "growth_rev": round(rev_growth, 1),
            "growth_eps": round(earn_growth, 1)
        }
    except:
        return None

def get_market_overview(tickers):
    try:
        data = yf.download(tickers, period="1mo", progress=False, timeout=5, group_by='ticker', auto_adjust=False)
        
        leaders = []
        for t in tickers[:5]:
            try:
                curr = data[t]['Close'].iloc[-1]
                prev = data[t]['Close'].iloc[-2]
                chg = ((curr - prev) / prev) * 100
                leaders.append({"ticker": t, "price": curr, "change": chg})
            except: pass

        changes = []
        for t in tickers:
            try:
                if len(data[t]) > 10:
                    start = data[t]['Close'].iloc[0]
                    end = data[t]['Close'].iloc[-1]
                    m_chg = ((end - start) / start) * 100
                    changes.append({"ticker": t, "m_change": m_chg, "price": end})
            except: pass
        
        changes.sort(key=lambda x: x['m_change'])
        losers = changes[:5]
        changes.sort(key=lambda x: x['m_change'], reverse=True)
        gainers = changes[:5]
        
        return leaders, gainers, losers
    except:
        return [], [], []

# --- FUNKCJE TECHNICZNE ---
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_stock(ticker, strategy, params):
    try:
        data = yf.download(ticker, period="1y", progress=False, timeout=2, auto_adjust=False)
        if len(data) < 50: return None
        close = data['Close']
        
        res = None
        chart_lines = {}
        
        if strategy == "RSI":
            rsi = calc_rsi(close, 14)
            curr = rsi.iloc[-1]
            if curr <= params['rsi_threshold']:
                res = {"info": f"RSI: {round(curr, 1)}", "val": round(curr, 1), "name": "RSI"}
                chart_lines = {'RSI': rsi}
        
        elif strategy == "SMA":
            sma = close.rolling(window=params['sma_period']).mean()
            if close.iloc[-1] > sma.iloc[-1]:
                res = {"info": "Cena nad SMA", "val": round(sma.iloc[-1], 2), "name": "SMA"}
                chart_lines = {'SMA': sma}
        
        if res:
            return {
                "ticker": ticker, 
                "price": round(close.iloc[-1], 2),
                "change": round(((close.iloc[-1]-close.iloc[-2])/close.iloc[-2])*100, 2),
                "details": res, 
                "chart_data": data[['Close']].copy(), 
                "extra_lines": chart_lines
            }
    except: return None
    return None

# --- INTERFEJS ---

with st.sidebar:
    st.header("KOLgejt 7.0")
    market_choice = st.radio("Giełda:", ["🇺🇸 S&P 500", "💻 Nasdaq 100", "🇵🇱 WIG20 (GPW)"])
    st.divider()
    strat = st.selectbox("Skaner:", ["RSI (Wyprzedanie)", "SMA (Trend)"])
    params = {}
    if "RSI" in strat: params['rsi_threshold'] = st.slider("RSI <", 20, 80, 40)
    elif "SMA" in strat: params['sma_period'] = st.slider("SMA Period", 10, 200, 50)
    st.caption(f"Aktualizacja: {datetime.now().strftime('%H:%M')}")

c1, c2 = st.columns([3,1])
with c1: st.title("📈 KOLgejt")
with c2: 
    if st.button("🔄 Odśwież"): st.rerun()

if "WIG20" in market_choice: tickers=WIG20_FULL; market="WIG20"
elif "Nasdaq" in market_choice: tickers=NASDAQ_TOP; market="Nasdaq 100"
else: tickers=SP500_TOP; market="S&P 500"

# --- 1. MARKET OVERVIEW ---
st.subheader(f"🔥 Pulpit: {market}")
with st.spinner("Analiza rynku..."):
    leaders, gainers, losers = get_market_overview(tickers)

cols = st.columns(5)
for i, l in enumerate(leaders):
    with cols[i]: st.metric(l['ticker'].replace('.WA',''), f"{l['price']:.2f}", f"{l['change']:.2f}%")

st.write("---")

# SEKCJA WZROSTÓW I SPADKÓW (PIONOWO - JEDEN POD DRUGIM)

# WZROSTY
st.markdown("### 🟩 Top 5 Wzrostów (Miesiąc)")
if gainers:
    gc = st.columns(5)
    for i, g in enumerate(gainers):
        with gc[i]: st.metric(g['ticker'].replace('.WA',''), f"{g['price']:.2f}", f"+{g['m_change']:.2f}%", delta_color="normal")
else: st.write("Brak danych.")

st.write("") # Odstęp

# SPADKI
st.markdown("### 🔻 Top 5 Spadków (Miesiąc)")
if losers:
    lc = st.columns(5)
    for i, l in enumerate(losers):
        with lc[i]: st.metric(l['ticker'].replace('.WA',''), f"{l['price']:.2f}", f"{l['m_change']:.2f}%", delta_color="normal")
else: st.write("Brak danych.")

st.write("---")

# --- 2. EARNINGS SLIDER (STYL WEBULL) ---
st.subheader("📢 Raporty Finansowe (Styl Webull)")

earnings_html = '<div class="scroll-container">'
# Pobieramy dane dla pierwszych 10 spółek z listy
with st.spinner("Generuję karty Earnings..."):
    for t in tickers[:10]:
        e = get_earnings_card_data(t)
        if e:
            card = f"""
            <div class="webull-card">
                <div class="card-header">{e['ticker'].replace('.WA','')}</div>
                <table class="webull-table">
                    <thead>
                        <tr>
                            <th>Parameters</th>
                            <th>Expected ($)</th>
                            <th>Numbers ($)</th>
                            <th>Beat/Miss</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="row-purple">
                            <td><strong>EPS</strong></td>
                            <td>{e['eps_est']}</td>
                            <td>{e['eps_act']}</td>
                            <td class="{e['eps_class']}">{e['eps_res']}</td>
                        </tr>
                        <tr class="row-purple">
                            <td><strong>Revenue</strong></td>
                            <td>{e['rev_est']}</td>
                            <td>{e['rev_act']}</td>
                            <td class="{e['rev_class']}">{e['rev_res']}</td>
                        </tr>
                    </tbody>
                </table>
                <div class="logo-section">
                    <img src="{e['logo']}" class="big-logo" onerror="this.style.display='none'">
                </div>
                <div class="bottom-stats">
                    <div>Revenue Growth: <span class="{'stat-up' if e['growth_rev']>0 else 'stat-down'}">{e['growth_rev']}% YoY</span></div>
                    <div>EPS Growth: <span class="{'stat-up' if e['growth_eps']>0 else 'stat-down'}">{e['growth_eps']}% YoY</span></div>
                </div>
            </div>
            """
            earnings_html += card
earnings_html += "</div>"

st.markdown(earnings_html, unsafe_allow_html=True)

st.write("---")

# --- 3. SKANER ---
st.subheader(f"📡 Skaner ({strat.split()[0]})")
if st.button(f"🔍 SKANUJ {market}", type="primary", use_container_width=True):
    prog = st.progress(0); stat = st.empty(); found = []
    for i, t in enumerate(tickers):
        if i%5==0: prog.progress((i+1)/len(tickers)); stat.text(f"Analiza: {t}")
        res = analyze_stock(t, strat.split()[0], params)
        if res: found.append(res)
    prog.empty(); stat.empty()
    
    if found:
        st.success(f"Znaleziono: {len(found)}")
        for item in found:
            with st.expander(f"{item['ticker']} ({item['change']}%) - {item['price']}", expanded=True):
                c1, c2 = st.columns([1,2])
                with c1:
                    st.write(f"**{item['details']['info']}**")
                    st.metric(item['details']['name'], item['details']['val'])
                    l = f"https://finance.yahoo.com/quote/{item['ticker']}"
                    st.link_button("Yahoo Finance", l)
                with c2:
                    ch = item['chart_data'].tail(60)
                    for k,v in item['extra_lines'].items(): ch[k]=v
                    st.line_chart(ch)
    else: st.warning("Brak wyników.")
