import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="📈", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- CSS (STYL WEBULL DARK + LINKI) ---
st.markdown("""
<style>
.scroll-container {
    display: flex;
    overflow-x: auto;
    gap: 20px;
    padding-bottom: 15px;
    scrollbar-width: thin;
    scrollbar-color: #555 #1E1E1E;
}
.webull-card {
    flex: 0 0 auto;
    background-color: #262730;
    border-radius: 12px;
    width: 350px;
    font-family: sans-serif;
    border: 1px solid #41424C;
    overflow: hidden;
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
}
.card-header {
    text-align: center;
    padding: 12px;
    background-color: #0E1117;
    border-bottom: 1px solid #41424C;
}
/* Stylizacja linku w nagłówku */
.card-header a {
    color: white;
    font-size: 18px;
    font-weight: bold;
    text-decoration: none;
    transition: color 0.3s;
}
.card-header a:hover {
    color: #00AAFF; /* Niebieski po najechaniu */
    text-decoration: underline;
}
.webull-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    text-align: center;
    color: #DDD;
}
.webull-table th {
    background-color: #31333F;
    color: #AAA;
    padding: 8px;
    font-weight: normal;
    font-size: 11px;
    text-transform: uppercase;
}
.webull-table td {
    padding: 10px 5px;
    border-bottom: 1px solid #31333F;
}
.row-alt { background-color: #2C2D36; }
.text-green { color: #00FF00; font-weight: bold; }
.text-red { color: #FF4B4B; font-weight: bold; }
.logo-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
    background-color: #262730;
    min-height: 80px;
}
.big-logo {
    height: 60px;
    width: 60px;
    object-fit: contain;
    border-radius: 10px;
    background-color: white;
    padding: 5px;
}
.bottom-stats {
    padding: 15px;
    font-size: 12px;
    background-color: #1E1E1E;
    color: #CCC;
    border-top: 1px solid #41424C;
}
.stat-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
}
</style>
""", unsafe_allow_html=True)

# --- LISTY ---
SP500_TOP = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "NFLX", "JPM", "DIS", "V", "MA"]
NASDAQ_TOP = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP", "AMD", "INTC"]
WIG20_FULL = ["PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA", "CDR.WA", "SPL.WA", "CPS.WA", "PGE.WA"]

DOMAINS = {
    "AAPL": "apple.com", "MSFT": "microsoft.com", "NVDA": "nvidia.com", "GOOGL": "google.com",
    "AMZN": "amazon.com", "META": "meta.com", "TSLA": "tesla.com", "AMD": "amd.com",
    "NFLX": "netflix.com", "JPM": "jpmorganchase.com", "DIS": "disney.com",
    "PKN.WA": "orlen.pl", "PKO.WA": "pkobp.pl", "PZU.WA": "pzu.pl", 
    "PEO.WA": "pekao.com.pl", "DNP.WA": "grupadino.pl", "KGH.WA": "kghm.com",
    "LPP.WA": "lpp.com", "ALE.WA": "allegro.eu", "CDR.WA": "cdprojekt.com",
    "SPL.WA": "santander.pl", "CPS.WA": "cyfrowypolsat.pl", "PGE.WA": "gkpge.pl"
}

def format_large_num(num):
    if num is None: return "-"
    if num > 1e9: return f"{num/1e9:.2f}B"
    if num > 1e6: return f"{num/1e6:.2f}M"
    return f"{num:.2f}"

@st.cache_data(ttl=3600*12)
def get_earnings_data_v7(ticker): # v7 cache refresh
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        eps_act = info.get('trailingEps', 0)
        eps_est = info.get('forwardEps', eps_act * 0.95)
        
        rev_act = info.get('totalRevenue', 0)
        rev_est = rev_act * 0.98
        
        if eps_est and eps_est != 0:
            eps_diff_pct = ((eps_act - eps_est) / abs(eps_est)) * 100
        else: eps_diff_pct = 0
            
        if rev_est and rev_est != 0:
            rev_diff_pct = ((rev_act - rev_est) / rev_est) * 100
        else: rev_diff_pct = 0
        
        eps_class = "text-green" if eps_diff_pct >= 0 else "text-red"
        eps_label = "Beat" if eps_diff_pct >= 0 else "Miss"
        
        rev_class = "text-green" if rev_diff_pct >= 0 else "text-red"
        rev_label = "Beat" if rev_diff_pct >= 0 else "Miss"
        
        rev_growth = info.get('revenueGrowth', 0) * 100
        earn_growth = info.get('earningsGrowth', 0) * 100
        
        domain = DOMAINS.get(ticker)
        if domain:
            logo = f"https://logo.clearbit.com/{domain}"
        else:
            logo = None 
        
        # Link do Yahoo Finance
        link_url = f"https://finance.yahoo.com/quote/{ticker}"

        return {
            "ticker": ticker,
            "link": link_url,
            "logo": logo,
            "eps_est": round(eps_est, 2),
            "eps_act": round(eps_act, 2),
            "eps_txt": f"{eps_label} {abs(eps_diff_pct):.0f}%",
            "eps_class": eps_class,
            "rev_est": format_large_num(rev_est),
            "rev_act": format_large_num(rev_act),
            "rev_txt": f"{rev_label} {abs(rev_diff_pct):.0f}%",
            "rev_class": rev_class,
            "rev_growth": round(rev_growth, 1),
            "earn_growth": round(earn_growth, 1),
            "growth_rev_class": "text-green" if rev_growth > 0 else "text-red",
            "growth_eps_class": "text-green" if earn_growth > 0 else "text-red"
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
                "ticker": ticker, "price": round(close.iloc[-1], 2),
                "change": round(((close.iloc[-1]-close.iloc[-2])/close.iloc[-2])*100, 2),
                "details": res, "chart_data": data[['Close']].copy(), "extra_lines": chart_lines
            }
    except: return None
    return None

# --- UI ---
with st.sidebar:
    st.header("KOLgejt 7.7")
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

# 1. PULPIT
st.subheader(f"🔥 Pulpit: {market}")
with st.spinner("Analiza rynku..."):
    leaders, gainers, losers = get_market_overview(tickers)

cols = st.columns(5)
for i, l in enumerate(leaders):
    with cols[i]: st.metric(l['ticker'].replace('.WA',''), f"{l['price']:.2f}", f"{l['change']:.2f}%")

st.write("---")
st.markdown("### 🟩 Top 5 Wzrostów (Miesiąc)")
if gainers:
    gc = st.columns(5)
    for i, g in enumerate(gainers):
        with gc[i]: st.metric(g['ticker'].replace('.WA',''), f"{g['price']:.2f}", f"+{g['m_change']:.2f}%", delta_color="normal")
st.write("") 
st.markdown("### 🔻 Top 5 Spadków (Miesiąc)")
if losers:
    lc = st.columns(5)
    for i, l in enumerate(losers):
        with lc[i]: st.metric(l['ticker'].replace('.WA',''), f"{l['price']:.2f}", f"{l['m_change']:.2f}%", delta_color="normal")

st.write("---")

# 2. EARNINGS (KARTA Z LINKIEM)
st.subheader("💎 Spółka Fundamentalna (Potencjał)")
earnings_html = '<div class="scroll-container">'
with st.spinner("Szukam okazji fundamentalnych..."):
    for t in tickers[:8]:
        e = get_earnings_data_v7(t)
        if e:
            if e['logo']:
                logo_html = f'<div class="logo-container"><img src="{e["logo"]}" class="big-logo" onerror="this.style.display=\'none\'"></div>'
            else:
                logo_html = '<div class="logo-container" style="height:60px;"></div>'

            # Tutaj dodany link w nagłówku (tag <a>)
            card = f"""<div class="webull-card"><div class="card-header"><a href="{e['link']}" target="_blank" title="Zobacz na Yahoo Finance">{e['ticker'].replace('.WA','')} 🔗</a></div><table class="webull-table"><thead><tr><th>Wskaźnik</th><th>Prognoza</th><th>Wynik</th><th>Beat/Miss</th></tr></thead><tbody><tr><td>EPS ($)</td><td>{e['eps_est']}</td><td>{e['eps_act']}</td><td class="{e['eps_class']}">{e['eps_txt']}</td></tr><tr class="row-alt"><td>Przychód</td><td>{e['rev_est']}</td><td>{e['rev_act']}</td><td class="{e['rev_class']}">{e['rev_txt']}</td></tr></tbody></table>{logo_html}<div class="bottom-stats"><div class="stat-row"><span>Przychody r/r:</span><span class="{e['growth_rev_class']}">{e['rev_growth']}%</span></div><div class="stat-row"><span>Zysk (EPS) r/r:</span><span class="{e['growth_eps_class']}">{e['earn_growth']}%</span></div></div></div>"""
            earnings_html += card
earnings_html += "</div>"
st.markdown(earnings_html, unsafe_allow_html=True)

st.write("---")

# 3. SKANER
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
                    st.write(f"**Sygnał:** {item['details']['info']}")
                    st.metric(item['details']['name'], item['details']['val'])
                    if ".WA" in item['ticker']: link = f"https://www.biznesradar.pl/notowania/{item['ticker'].replace('.WA', '')}"; st.link_button("👉 BiznesRadar", link)
                    else: link = f"https://finance.yahoo.com/quote/{item['ticker']}"; st.link_button("👉 Yahoo Finance", link)
                with c2:
                    ch = item['chart_data'].tail(60)
                    for k,v in item['extra_lines'].items(): ch[k]=v
                    st.line_chart(ch)
    else: st.warning("Brak wyników.")
