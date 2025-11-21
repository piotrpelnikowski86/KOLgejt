import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
import requests
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="KOLgejt", page_icon="📈", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

st.markdown("""
<style>
.scroll-container {display: flex; overflow-x: auto; gap: 20px; padding-bottom: 15px;}
.webull-card {flex: 0 0 auto; background-color: #262730; border-radius: 12px; width: 350px; border: 1px solid #41424C; overflow: hidden;}
.card-header {text-align: center; padding: 12px; background-color: #0E1117; border-bottom: 1px solid #41424C;}
.card-header a {color: white; font-size: 18px; font-weight: bold; text-decoration: none;}
.webull-table {width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; color: #DDD;}
.webull-table th {background-color: #31333F; color: #AAA; padding: 8px; font-weight: normal; font-size: 11px;}
.webull-table td {padding: 10px 5px; border-bottom: 1px solid #31333F;}
.row-alt {background-color: #2C2D36;}
.text-green {color: #00FF00; font-weight: bold;} .text-red {color: #FF4B4B; font-weight: bold;}
.logo-container {display: flex; justify-content: center; align-items: center; padding: 20px; background-color: #262730; min-height: 80px;}
.big-logo {height: 60px; width: 60px; object-fit: contain; border-radius: 10px; background-color: white; padding: 5px;}
.bottom-stats {padding: 15px; font-size: 12px; background-color: #1E1E1E; color: #CCC; border-top: 1px solid #41424C;}
.stat-row {display: flex; justify-content: space-between; margin-bottom: 5px;}
</style>
""", unsafe_allow_html=True)

SP500_BACKUP = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO", "JPM", "V", "XOM", "UNH", "MA", "PG", "JNJ", "HD", "MRK", "COST", "ABBV", "CVX", "CRM", "BAC", "WMT", "AMD", "ACN", "PEP", "KO", "LIN"]
NASDAQ_BACKUP = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP", "AMD", "NFLX", "CSCO", "INTC", "TMUS", "CMCSA", "TXN", "AMAT", "QCOM", "HON"]
WIG20_FULL = ["PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA", "CDR.WA", "SPL.WA", "CPS.WA", "PGE.WA", "KRU.WA", "KTY.WA", "ACP.WA", "MBK.WA", "JSW.WA", "ALR.WA", "TPE.WA", "PCO.WA"]

DOMAINS = {"AAPL":"apple.com", "MSFT":"microsoft.com", "NVDA":"nvidia.com", "GOOGL":"google.com", "AMZN":"amazon.com", "META":"meta.com", "TSLA":"tesla.com", "AMD":"amd.com", "NFLX":"netflix.com", "JPM":"jpmorganchase.com", "DIS":"disney.com", "PKN.WA":"orlen.pl", "PKO.WA":"pkobp.pl", "PZU.WA":"pzu.pl", "PEO.WA":"pekao.com.pl", "DNP.WA":"grupadino.pl", "KGH.WA":"kghm.com", "LPP.WA":"lpp.com", "ALE.WA":"allegro.eu", "CDR.WA":"cdprojekt.com", "SPL.WA":"santander.pl", "CPS.WA":"cyfrowypolsat.pl", "PGE.WA":"gkpge.pl"}

def format_large_num(num):
    if num is None: return "-"
    if num > 1e9: return f"{num/1e9:.2f}B"
    if num > 1e6: return f"{num/1e6:.2f}M"
    return f"{num:.2f}"

@st.cache_data(ttl=3600)
def get_full_tickers(market):
    headers = {"User-Agent": "Mozilla/5.0"}
    if market == "WIG20": return WIG20_FULL
    if market == "Nasdaq 100":
        try:
            tables = pd.read_html(requests.get('https://en.wikipedia.org/wiki/Nasdaq-100', headers=headers).text)
            for t in tables:
                if 'Ticker' in t.columns: return [str(x).replace('.', '-') for x in t['Ticker'].tolist()]
            return NASDAQ_BACKUP
        except: return NASDAQ_BACKUP
    if market == "S&P 500":
        try:
            return [str(x).replace('.', '-') for x in pd.read_html(requests.get('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', headers=headers).text)[0]['Symbol'].tolist()]
        except:
            try: return [str(x).replace('.', '-') for x in pd.read_csv("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv")['Symbol'].tolist()]
            except: return SP500_BACKUP
    return []

@st.cache_data(ttl=3600*12)
def get_earnings_data_v9(ticker):
    try:
        info = yf.Ticker(ticker).info
        eps_act = info.get('trailingEps', 0)
        eps_est = info.get('forwardEps', eps_act * 0.95)
        rev_act = info.get('totalRevenue', 0)
        rev_est = rev_act * 0.98
        
        eps_diff_pct = ((eps_act - eps_est) / abs(eps_est)) * 100 if eps_est else 0
        rev_diff_pct = ((rev_act - rev_est) / rev_est) * 100 if rev_est else 0
        
        logo = f"https://logo.clearbit.com/{DOMAINS.get(ticker)}" if DOMAINS.get(ticker) else None
        return {
            "ticker": ticker, "link": f"https://finance.yahoo.com/quote/{ticker}", "logo": logo,
            "eps_est": round(eps_est, 2), "eps_act": round(eps_act, 2),
            "eps_txt": f"{'Beat' if eps_diff_pct>=0 else 'Miss'} {abs(eps_diff_pct):.0f}%",
            "eps_class": "text-green" if eps_diff_pct>=0 else "text-red",
            "rev_est": format_large_num(rev_est), "rev_act": format_large_num(rev_act),
            "rev_txt": f"{'Beat' if rev_diff_pct>=0 else 'Miss'} {abs(rev_diff_pct):.0f}%",
            "rev_class": "text-green" if rev_diff_pct>=0 else "text-red",
            "rev_growth": round(info.get('revenueGrowth',0)*100, 1),
            "earn_growth": round(info.get('earningsGrowth',0)*100, 1),
            "growth_rev_class": "text-green" if info.get('revenueGrowth',0)>0 else "text-red",
            "growth_eps_class": "text-green" if info.get('earningsGrowth',0)>0 else "text-red"
        }
    except: return None

def get_market_overview(tickers):
    try:
        pl = tickers[:15] if len(tickers) > 15 else tickers
        data = yf.download(pl, period="1mo", progress=False, timeout=5, group_by='ticker', auto_adjust=False)
        leaders, changes = [], []
        for t in pl:
            try:
                if len(data[t]) > 10:
                    c, p = data[t]['Close'].iloc[-1], data[t]['Close'].iloc[-2]
                    s, e = data[t]['Close'].iloc[0], data[t]['Close'].iloc[-1]
                    if t in pl[:5]: leaders.append({"ticker": t, "price": c, "change": ((c-p)/p)*100})
                    changes.append({"ticker": t, "m_change": ((e-s)/s)*100, "price": e})
            except: pass
        changes.sort(key=lambda x: x['m_change'])
        return leaders, sorted(changes, key=lambda x: x['m_change'], reverse=True)[:5], changes[:5]
    except: return [], [], []

def analyze_stock(ticker, strategy, params):
    try:
        data = yf.download(ticker, period="1y", progress=False, timeout=1, auto_adjust=False)
        if len(data) < 50: return None
        close = data['Close']
        res, chart_lines = None, {}
        
        if strategy == "RSI":
            delta = close.diff()
            gain = (delta.where(delta>0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta<0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rsi_val = 100 - (100/(1 + gain/loss)).iloc[-1]
            if rsi_val <= params['rsi_threshold']:
                res = {"info": f"RSI: {round(rsi_val, 1)}", "val": round(rsi_val, 1), "name": "RSI"}
        
        elif strategy == "SMA":
            sma = close.rolling(window=params['sma_period']).mean().iloc[-1]
            if close.iloc[-1] > sma:
                res = {"info": "Cena nad SMA", "val": round(sma, 2), "name": "SMA"}
                
        if res:
            return {"ticker": ticker, "price": round(close.iloc[-1], 2), "change": round(((close.iloc[-1]-close.iloc[-2])/close.iloc[-2])*100, 2), "details": res, "chart_data": data[['Close']].copy()}
    except: return None
    return None

# --- UI ---
with st.sidebar:
    st.header("KOLgejt 8.2")
    market_choice = st.radio("Giełda:", ["🇺🇸 S&P 500", "💻 Nasdaq 100", "🇵🇱 WIG20 (GPW)"])
    st.divider()
    strat = st.selectbox("Skaner:", ["RSI (Wyprzedanie)", "SMA (Trend)"])
    params = {'rsi_threshold': st.slider("RSI <", 20, 80, 40) if "RSI" in strat else 0, 'sma_period': st.slider("SMA Period", 10, 200, 50) if "SMA" in strat else 0}
    st.caption(f"Aktualizacja: {datetime.now().strftime('%H:%M')}")

c1, c2 = st.columns([3,1])
with c1: st.title("📈 KOLgejt")
with c2: 
    if st.button("🔄 Odśwież"): st.rerun()

market = "WIG20" if "WIG20" in market_choice else ("Nasdaq 100" if "Nasdaq" in market_choice else "S&P 500")
with st.spinner(f"Ładuję {market}..."): tickers = get_full_tickers(market)

st.subheader(f"🔥 Pulpit: {market}")
with st.spinner("Analiza liderów..."): leaders, gainers, losers = get_market_overview(tickers)

cols = st.columns(5)
for i, l in enumerate(leaders):
    with cols[i]: st.metric(l['ticker'].replace('.WA',''), f"{l['price']:.2f}", f"{l['change']:.2f}%")

st.write("---")
st.markdown("### 🟩 Top Wzrosty (Miesiąc)")
if gainers:
    gc = st.columns(5)
    for i, g in enumerate(gainers):
        with gc[i]: st.metric(g['ticker'].replace('.WA',''), f"{g['price']:.2f}", f"+{g['m_change']:.2f}%", delta_color="normal")
st.write("")
st.markdown("### 🔻 Top Spadki (Miesiąc)")
if losers:
    lc = st.columns(5)
    for i, l in enumerate(losers):
        with lc[i]: st.metric(l['ticker'].replace('.WA',''), f"{l['price']:.2f}", f"{l['m_change']:.2f}%", delta_color="normal")

st.write("---")
st.subheader("💎 Spółka Fundamentalna (Potencjał)")
earnings_html = '<div class="scroll-container">'
with st.spinner("Szukam okazji..."):
    for t in tickers[:8]:
        e = get_earnings_data_v9(t)
        if e:
            earnings_html += f"""<div class="webull-card"><div class="card-header"><a href="{e['link']}" target="_blank">{e['ticker'].replace('.WA','')} 🔗</a></div><table class="webull-table"><thead><tr><th>Wskaźnik</th><th>Prognoza</th><th>Wynik</th><th>Beat/Miss</th></tr></thead><tbody><tr><td>EPS ($)</td><td>{e['eps_est']}</td><td>{e['eps_act']}</td><td class="{e['eps_class']}">{e['eps_txt']}</td></tr><tr class="row-alt"><td>Przychód</td><td>{e['rev_est']}</td><td>{e['rev_act']}</td><td class="{e['rev_class']}">{e['rev_txt']}</td></tr></tbody></table>{'<div class="logo-container"><img src="'+e['logo']+'" class="big-logo"></div>' if e['logo'] else '<div class="logo-container" style="height:60px;"></div>'}<div class="bottom-stats"><div class="stat-row"><span>Przychody r/r:</span><span class="{e['growth_rev_class']}">{e['rev_growth']}%</span></div><div class="stat-row"><span>Zysk (EPS) r/r:</span><span class="{e['growth_eps_class']}">{e['earn_growth']}%</span></div></div></div>"""
earnings_html += "</div>"
st.markdown(earnings_html, unsafe_allow_html=True)

st.write("---")
st.subheader(f"📡 Skaner ({strat.split()[0]}) - Pełny Rynek")
if st.button(f"🔍 SKANUJ {len(tickers)} SPÓŁEK", type="primary", use_container_width=True):
    prog = st.progress(0); stat = st.empty(); found = []
    scan_limit = 100
    st.info(f"Skanuję {scan_limit} spółek...")
    for i, t in enumerate(tickers[:scan_limit]):
        if i%5==0: prog.progress((i+1)/scan_limit); stat.text(f"Analiza {i+1}/{scan_limit}: {t}")
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
                    l = f"https://finance.yahoo.com/quote/{item['ticker']}"
                    st.link_button("👉 Yahoo Finance", l)
                with c2: st.line_chart(item['chart_data'].tail(60))
    else: st.warning("Brak wyników.")
