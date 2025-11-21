import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
import requests
from io import StringIO
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
    padding: 10px 5px;
    width: 100%;
    scrollbar-width: thin;
    scrollbar-color: #555 #1E1E1E;
}
.webull-card {
    flex: 0 0 auto;
    background-color: #262730;
    border-radius: 12px;
    width: 320px;
    font-family: sans-serif;
    border: 1px solid #41424C;
    overflow: hidden;
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    position: relative;
}
/* Wyróżnienie dla Strong Buy */
.strong-buy-card {
    border: 2px solid #FFD700; /* Złota ramka */
    box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
}
.badge {
    position: absolute;
    top: 10px;
    right: 10px;
    background-color: #FFD700;
    color: black;
    font-size: 10px;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 4px;
    z-index: 10;
}
.card-header {
    text-align: center;
    padding: 12px;
    background-color: #0E1117;
    border-bottom: 1px solid #41424C;
}
.card-header a {color: white; font-size: 18px; font-weight: bold; text-decoration: none;}
.webull-table {width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; color: #DDD;}
.webull-table th {background-color: #31333F; color: #AAA; padding: 6px; font-weight: normal;}
.webull-table td {padding: 8px 4px; border-bottom: 1px solid #31333F;}
.row-alt { background-color: #2C2D36; }
.text-green { color: #00FF00; font-weight: bold; }
.text-red { color: #FF4B4B; font-weight: bold; }
.logo-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 15px;
    background-color: #262730;
    min-height: 70px;
}
.big-logo {height: 50px; width: 50px; object-fit: contain; border-radius: 8px; background-color: white; padding: 4px;}
.bottom-stats {padding: 10px; font-size: 11px; background-color: #1E1E1E; color: #CCC; border-top: 1px solid #41424C;}
.stat-row {display: flex; justify-content: space-between; margin-bottom: 4px;}
</style>
""", unsafe_allow_html=True)

# --- DANE ---
# Używamy szerszych list, żeby mieć z czego wybierać Top 5
SP500_POOL = ["NVDA", "META", "AMD", "AMZN", "MSFT", "GOOGL", "AAPL", "TSLA", "NFLX", "AVGO", "LLY", "JPM", "V", "MA", "COST", "PEP", "KO", "XOM", "CVX", "BRK-B", "DIS", "WMT", "HD", "PG", "MRK", "ABBV", "CRM", "ACN", "LIN", "ADBE"]
NASDAQ_POOL = ["NVDA", "META", "AMD", "AMZN", "MSFT", "GOOGL", "AAPL", "TSLA", "NFLX", "AVGO", "COST", "PEP", "INTC", "CSCO", "TMUS", "CMCSA", "AMGN", "TXN", "QCOM", "HON", "INTU", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADP", "LRCX"]
WIG20_POOL = ["PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA", "CDR.WA", "SPL.WA", "CPS.WA", "PGE.WA", "KRU.WA", "KTY.WA", "ACP.WA", "MBK.WA", "JSW.WA", "ALR.WA", "TPE.WA"]

DOMAINS = {
    "AAPL": "apple.com", "MSFT": "microsoft.com", "NVDA": "nvidia.com", "GOOGL": "google.com",
    "AMZN": "amazon.com", "META": "meta.com", "TSLA": "tesla.com", "AMD": "amd.com",
    "NFLX": "netflix.com", "JPM": "jpmorganchase.com", "DIS": "disney.com", "AVGO": "broadcom.com",
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

# --- LOGIKA FUNDAMENTALNA (SORTOWANIE I STRONG BUY) ---

@st.cache_data(ttl=3600*4)
def scan_fundamentals(tickers_list):
    """Skanuje listę i zwraca: 1. Top 5 Fundamentalnych, 2. Top 1 Strong Buy"""
    fundamental_data = []
    strong_buys = []
    
    for t in tickers_list:
        try:
            stock = yf.Ticker(t)
            info = stock.info
            
            # Dane podstawowe
            rev_growth = info.get('revenueGrowth', 0)
            earn_growth = info.get('earningsGrowth', 0)
            
            # Jeśli brak danych, pomijamy w rankingu fundamentalnym
            if rev_growth is None or earn_growth is None: continue
            
            # Obliczenie "Score" (siły spółki)
            score = (rev_growth * 100) + (earn_growth * 100)
            
            # Dane do karty
            eps_act = info.get('trailingEps', 0)
            eps_est = info.get('forwardEps', eps_act * 0.95)
            rev_act = info.get('totalRevenue', 0)
            rev_est = rev_act * 0.98
            
            # Beat calculation
            eps_diff_pct = ((eps_act - eps_est) / abs(eps_est)) * 100 if eps_est else 0
            rev_diff_pct = ((rev_act - rev_est) / rev_est) * 100 if rev_est else 0
            
            # Logo
            domain = DOMAINS.get(t)
            logo = f"https://logo.clearbit.com/{domain}" if domain else None
            link = f"https://finance.yahoo.com/quote/{t}"
            
            data_pack = {
                "ticker": t, "link": link, "logo": logo, "score": score,
                "eps_est": round(eps_est, 2), "eps_act": round(eps_act, 2),
                "eps_txt": f"{'Beat' if eps_diff_pct>=0 else 'Miss'} {abs(eps_diff_pct):.0f}%",
                "eps_cls": "text-green" if eps_diff_pct>=0 else "text-red",
                "rev_est": format_large_num(rev_est), "rev_act": format_large_num(rev_act),
                "rev_txt": f"{'Beat' if rev_diff_pct>=0 else 'Miss'} {abs(rev_diff_pct):.0f}%",
                "rev_cls": "text-green" if rev_diff_pct>=0 else "text-red",
                "rev_growth": round(rev_growth*100, 1),
                "earn_growth": round(earn_growth*100, 1),
                "g_rev_cls": "text-green" if rev_growth>0 else "text-red",
                "g_eps_cls": "text-green" if earn_growth>0 else "text-red",
                # Dla Strong Buy
                "recommendation": info.get('recommendationKey', 'none'),
                "target_price": info.get('targetMeanPrice', 0),
                "current_price": info.get('currentPrice', info.get('previousClose', 0))
            }
            
            fundamental_data.append(data_pack)
            
            # Sprawdzenie czy to Strong Buy
            if data_pack['recommendation'] == 'strong_buy' and data_pack['target_price'] > data_pack['current_price']:
                upside = ((data_pack['target_price'] - data_pack['current_price']) / data_pack['current_price']) * 100
                data_pack['upside'] = upside
                strong_buys.append(data_pack)
                
        except: continue

    # Sortowanie Top 5 (wg Score)
    fundamental_data.sort(key=lambda x: x['score'], reverse=True)
    top5 = fundamental_data[:5]
    
    # Sortowanie Strong Buy (wg Upside potential)
    strong_buys.sort(key=lambda x: x.get('upside', 0), reverse=True)
    best_pick = strong_buys[0] if strong_buys else None
    
    return top5, best_pick

# --- ANALIZA TECHNICZNA ---
def analyze_stock_tech(ticker, strategy, params):
    try:
        data = yf.download(ticker, period="1y", progress=False, timeout=1, auto_adjust=False)
        if len(data) < 50: return None
        close = data['Close']
        res = None
        
        if strategy == "RSI":
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            curr = rsi.iloc[-1]
            if curr <= params['rsi_threshold']:
                res = {"info": f"RSI: {round(curr, 1)}", "val": round(curr, 1), "name": "RSI"}
        
        elif strategy == "SMA":
            sma = close.rolling(window=params['sma_period']).mean()
            if close.iloc[-1] > sma.iloc[-1]:
                res = {"info": "Cena nad SMA", "val": round(sma.iloc[-1], 2), "name": "SMA"}
                
        if res:
            return {
                "ticker": ticker, "price": round(close.iloc[-1], 2),
                "change": round(((close.iloc[-1]-close.iloc[-2])/close.iloc[-2])*100, 2),
                "details": res, "chart_data": data[['Close']].copy()
            }
    except: return None
    return None

# --- PULPIT DANE ---
def get_market_overview(tickers):
    try:
        # Bierzemy max 15 do podglądu
        preview = tickers[:15]
        data = yf.download(preview, period="1mo", progress=False, timeout=5, group_by='ticker', auto_adjust=False)
        leaders, changes = [], []
        for t in preview:
            try:
                if len(data[t]) > 10:
                    c, p = data[t]['Close'].iloc[-1], data[t]['Close'].iloc[-2]
                    s = data[t]['Close'].iloc[0]
                    day_chg = ((c-p)/p)*100
                    mon_chg = ((c-s)/s)*100
                    if t in preview[:5]: leaders.append({"t": t, "p": c, "c": day_chg})
                    changes.append({"t": t, "mc": mon_chg, "p": c})
            except: pass
        changes.sort(key=lambda x: x['mc'])
        return leaders, sorted(changes, key=lambda x: x['mc'], reverse=True)[:5], changes[:5]
    except: return [], [], []

# --- UI ---
with st.sidebar:
    st.header("KOLgejt 9.0")
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

if "WIG20" in market_choice: 
    market="WIG20"; tickers=WIG20_POOL
elif "Nasdaq" in market_choice: 
    market="Nasdaq 100"; tickers=NASDAQ_POOL
else: 
    market="S&P 500"; tickers=SP500_POOL

# 1. PULPIT
st.subheader(f"🔥 Pulpit: {market}")
with st.spinner("Analiza liderów..."):
    leaders, gainers, losers = get_market_overview(tickers)

cols = st.columns(5)
for i, l in enumerate(leaders):
    with cols[i]: st.metric(l['t'].replace('.WA',''), f"{l['p']:.2f}", f"{l['c']:.2f}%")

st.write("---")
col_g, col_l = st.columns(2)
with col_g:
    st.markdown("### 🟩 Top Wzrosty (Miesiąc)")
    gc = st.columns(5)
    if gainers:
        for i, g in enumerate(gainers):
            with gc[i]: st.metric(g['t'].replace('.WA',''), f"{g['p']:.2f}", f"+{g['mc']:.2f}%", delta_color="normal")
with col_l:
    st.markdown("### 🔻 Top Spadki (Miesiąc)")
    lc = st.columns(5)
    if losers:
        for i, l in enumerate(losers):
            with lc[i]: st.metric(l['t'].replace('.WA',''), f"{l['p']:.2f}", f"{l['mc']:.2f}%", delta_color="normal")

st.write("---")

# POBIERANIE DANYCH FUNDAMENTALNYCH (JEDEN RAZ)
with st.spinner("Skanuję fundamenty i szukam perełek (to może chwilę potrwać)..."):
    top_funds, best_pick = scan_fundamentals(tickers)

# 2. ANALYST STRONG BUY (NOWA SEKCJA)
st.subheader("🏆 Analyst Strong Buy (Wybór Ekspertów)")
if best_pick:
    e = best_pick
    logo_html = f'<div class="logo-container"><img src="{e["logo"]}" class="big-logo"></div>' if e['logo'] else '<div class="logo-container" style="height:60px;"></div>'
    
    # Wyświetlamy jedną dużą kartę
    st.markdown(f"""
    <div class="webull-card strong-buy-card" style="margin: 0 auto; display: block;">
        <div class="badge">STRONG BUY</div>
        <div class="card-header"><a href="{e['link']}" target="_blank">{e['ticker'].replace('.WA','')} 🔗</a></div>
        <table class="webull-table">
            <thead><tr><th>Cel Cenowy</th><th>Potencjał</th><th>Wzrost EPS</th></tr></thead>
            <tbody>
                <tr>
                    <td>{e['target_price']} $</td>
                    <td class="text-green">+{e['upside']:.1f}%</td>
                    <td class="{e['g_eps_cls']}">{e['earn_growth']}%</td>
                </tr>
            </tbody>
        </table>
        {logo_html}
        <div class="bottom-stats" style="text-align:center;">
            Rekomendacja analityków: <strong>STRONG BUY</strong><br>
            Przewidywany zysk na akcji: {e['eps_est']} $
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("Brak spółek z oceną 'Strong Buy' i potencjałem wzrostu w tym indeksie.")

st.write("---")

# 3. TOP 5 FUNDAMENTALNE (POSORTOWANE)
st.subheader("💎 Top 5 Fundamentalnych (Największy Wzrost)")
if top_funds:
    earnings_html = '<div class="scroll-container">'
    for e in top_funds:
        logo_html = f'<div class="logo-container"><img src="{e["logo"]}" class="big-logo"></div>' if e['logo'] else '<div class="logo-container" style="height:60px;"></div>'
        card = f"""<div class="webull-card"><div class="card-header"><a href="{e['link']}" target="_blank">{e['ticker'].replace('.WA','')} 🔗</a></div><table class="webull-table"><thead><tr><th>Wskaźnik</th><th>Prognoza</th><th>Wynik</th><th>Beat/Miss</th></tr></thead><tbody><tr><td>EPS ($)</td><td>{e['eps_est']}</td><td>{e['eps_act']}</td><td class="{e['eps_cls']}">{e['eps_txt']}</td></tr><tr class="row-alt"><td>Przychód</td><td>{e['rev_est']}</td><td>{e['rev_act']}</td><td class="{e['rev_cls']}">{e['rev_txt']}</td></tr></tbody></table>{logo_html}<div class="bottom-stats"><div class="stat-row"><span>Przychody r/r:</span><span class="{e['g_rev_cls']}">{e['rev_growth']}%</span></div><div class="stat-row"><span>Zysk (EPS) r/r:</span><span class="{e['g_eps_cls']}">{e['earn_growth']}%</span></div></div></div>"""
        earnings_html += card
    earnings_html += "</div>"
    st.markdown(earnings_html, unsafe_allow_html=True)
else:
    st.write("Brak danych fundamentalnych.")

st.write("---")

# 4. SKANER
st.subheader(f"📡 Skaner Techniczny ({strat.split()[0]})")
if st.button(f"🔍 SKANUJ {len(tickers)} SPÓŁEK", type="primary", use_container_width=True):
    prog = st.progress(0); stat = st.empty(); found = []
    scan_limit = 100 # Limit dla płynności
    
    for i, t in enumerate(tickers[:scan_limit]):
        if i%5==0: prog.progress((i+1)/len(tickers[:scan_limit])); stat.text(f"Analiza: {t}")
        res = analyze_stock_tech(t, strat.split()[0], params)
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
                with c2: st.line_chart(item['chart_data'].tail(60))
    else: st.warning("Brak wyników.")
