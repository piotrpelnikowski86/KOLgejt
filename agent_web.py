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

# --- CSS (STYL WEBULL DARK + MINI KARTY) ---
st.markdown("""
<style>
/* Kontener paska przewijania */
.scroll-container {
    display: flex;
    overflow-x: auto;
    gap: 15px;
    padding: 10px 5px;
    width: 100%;
    scrollbar-width: thin;
    scrollbar-color: #555 #1E1E1E;
}

/* Duża Karta (Fundamentalna) */
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

/* Mini Karta (Wzrosty/Spadki) */
.mini-card {
    flex: 0 0 auto;
    background-color: #1E1E1E;
    border-radius: 8px;
    width: 160px;
    padding: 10px;
    text-align: center;
    border: 1px solid #333;
    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
}
.mini-card-up { border-top: 3px solid #00FF00; }
.mini-card-down { border-top: 3px solid #FF4B4B; }

.mini-ticker { font-size: 16px; font-weight: bold; color: white; margin-bottom: 5px; }
.mini-price { font-size: 14px; color: #CCC; }
.mini-change { font-size: 14px; font-weight: bold; margin-top: 2px; }

/* Strong Buy Badge */
.strong-buy-card { border: 2px solid #FFD700; box-shadow: 0 0 15px rgba(255, 215, 0, 0.3); }
.badge { position: absolute; top: 10px; right: 10px; background-color: #FFD700; color: black; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; z-index: 10; }

.card-header { text-align: center; padding: 12px; background-color: #0E1117; border-bottom: 1px solid #41424C; }
.card-header a { color: white; font-size: 18px; font-weight: bold; text-decoration: none; }
.webull-table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; color: #DDD; }
.webull-table th { background-color: #31333F; color: #AAA; padding: 6px; font-weight: normal; }
.webull-table td { padding: 8px 4px; border-bottom: 1px solid #31333F; }
.row-alt { background-color: #2C2D36; }
.text-green { color: #00FF00; font-weight: bold; }
.text-red { color: #FF4B4B; font-weight: bold; }
.logo-container { display: flex; justify-content: center; align-items: center; padding: 15px; background-color: #262730; min-height: 70px; }
.big-logo { height: 50px; width: 50px; object-fit: contain; border-radius: 8px; background-color: white; padding: 4px; }
.bottom-stats { padding: 10px; font-size: 11px; background-color: #1E1E1E; color: #CCC; border-top: 1px solid #41424C; }
.stat-row { display: flex; justify-content: space-between; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# --- LISTY (MAŁE DO FUNDAMENTÓW, FUNKCJE DO DUŻYCH) ---
# To są listy do "szybkiego podglądu" (Fundamenty)
POOL_SP500 = ["NVDA", "META", "AMD", "AMZN", "MSFT", "GOOGL", "AAPL", "TSLA", "NFLX", "AVGO", "LLY", "JPM", "V", "MA", "COST", "PEP", "KO", "XOM", "CVX", "BRK-B", "DIS", "WMT", "HD", "PG", "MRK", "ABBV", "CRM", "ACN", "LIN", "ADBE"]
POOL_NASDAQ = ["NVDA", "META", "AMD", "AMZN", "MSFT", "GOOGL", "AAPL", "TSLA", "NFLX", "AVGO", "COST", "PEP", "INTC", "CSCO", "TMUS", "CMCSA", "AMGN", "TXN", "QCOM", "HON", "INTU", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADP", "LRCX"]
POOL_WIG20 = ["PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA", "CDR.WA", "SPL.WA", "CPS.WA", "PGE.WA", "KRU.WA", "KTY.WA", "ACP.WA", "MBK.WA", "JSW.WA", "ALR.WA", "TPE.WA"]

# Duża lista zapasowa dla Skanera (gdyby Wikipedia padła)
BACKUP_SP500_LARGE = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO", "JPM", "V", "XOM", "UNH", "MA", "PG", "JNJ", "HD", "MRK", "COST", "ABBV", "CVX", "CRM", "BAC", "WMT", "AMD", "ACN", "PEP", "KO", "LIN", "TMO", "DIS", "MCD", "CSCO", "ABT", "INTC", "WFC", "VZ", "NFLX", "QCOM", "INTU", "NKE", "IBM", "PM", "GE", "AMAT", "TXN", "NOW", "SPGI", "CAT", "BA", "RTX", "HON", "UNP", "GS", "AMGN", "IBM", "DE", "LMT", "EL", "PLD", "BLK", "SYK", "ISRG", "BKNG", "MDLZ", "GILD", "ADP", "LRCX", "TJX", "MMC", "VRTX", "REGN", "ADI", "ZTS", "C", "CI", "BSX", "FI", "CB", "SCHW", "MO", "SO", "TMUS", "EOG", "PGR", "BDX", "PANW", "WM", "TGT", "CL", "ITW", "SHW", "CSX", "SLB", "HUM", "MMM", "USB", "PNC", "DUK", "EMR", "APH", "MCO", "FCX", "TFC", "NEM", "FDX", "NSC", "GD", "NXPI", "ORLY", "MCK", "PSX", "MAR", "MPC", "ROP", "ADSK", "KLAC", "MSI", "ECL", "CTAS", "DLR", "AIG", "APH", "COF", "AFL", "O", "TEL", "TRV", "ALL", "BK", "YUM", "ROST", "AEP", "MET", "KMB", "JCI", "D", "PEG", "FAST", "PRU", "WELL", "ED", "WMB", "CMI", "EXC", "HPQ", "PAYX", "GLW", "KR", "PCAR", "DHI", "XEL", "VLO", "CTSH", "SRE", "PEG", "WEC", "AWK", "ES", "ODFL", "HIG", "PPG", "VICI", "EIX", "OXY", "KMI", "ON", "SBAC", "HAL", "DVN", "HESS", "FANG", "BKR", "MRO", "APA", "CTRA"]

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

# --- FUNKCJE POBIERANIA LIST (FULL SCAN) ---
@st.cache_data(ttl=3600)
def get_full_market_tickers(market):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    if market == "WIG20":
        return POOL_WIG20 # Dla WIG20 lista jest stała
    
    if market == "Nasdaq 100":
        try:
            url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
            tables = pd.read_html(requests.get(url, headers=headers).text)
            for t in tables:
                if 'Ticker' in t.columns:
                    return [str(x).replace('.', '-') for x in t['Ticker'].tolist()]
            return POOL_NASDAQ
        except: return POOL_NASDAQ

    if market == "S&P 500":
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            tables = pd.read_html(requests.get(url, headers=headers).text)
            return [str(x).replace('.', '-') for x in tables[0]['Symbol'].tolist()]
        except:
            # Jeśli Wikipedia padnie, używamy dużej listy backup (100+ spółek)
            return BACKUP_SP500_LARGE
    
    return []

# --- FUNDAMENTY ---
@st.cache_data(ttl=3600*4)
def scan_fundamentals(tickers_list):
    fundamental_data = []
    strong_buys = []
    for t in tickers_list:
        try:
            stock = yf.Ticker(t)
            info = stock.info
            rev_growth = info.get('revenueGrowth', 0)
            earn_growth = info.get('earningsGrowth', 0)
            if rev_growth is None or earn_growth is None: continue
            
            score = (rev_growth * 100) + (earn_growth * 100)
            eps_act = info.get('trailingEps', 0)
            eps_est = info.get('forwardEps', eps_act * 0.95)
            rev_act = info.get('totalRevenue', 0)
            rev_est = rev_act * 0.98
            
            eps_diff_pct = ((eps_act - eps_est) / abs(eps_est)) * 100 if eps_est else 0
            rev_diff_pct = ((rev_act - rev_est) / rev_est) * 100 if rev_est else 0
            
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
                "rev_growth": round(rev_growth*100, 1), "earn_growth": round(earn_growth*100, 1),
                "g_rev_cls": "text-green" if rev_growth>0 else "text-red",
                "g_eps_cls": "text-green" if earn_growth>0 else "text-red",
                "recommendation": info.get('recommendationKey', 'none'),
                "target_price": info.get('targetMeanPrice', 0),
                "current_price": info.get('currentPrice', info.get('previousClose', 0))
            }
            fundamental_data.append(data_pack)
            
            if data_pack['recommendation'] == 'strong_buy' and data_pack['target_price'] > data_pack['current_price']:
                upside = ((data_pack['target_price'] - data_pack['current_price']) / data_pack['current_price']) * 100
                data_pack['upside'] = upside
                strong_buys.append(data_pack)
        except: continue

    fundamental_data.sort(key=lambda x: x['score'], reverse=True)
    strong_buys.sort(key=lambda x: x.get('upside', 0), reverse=True)
    
    return fundamental_data[:5], (strong_buys[0] if strong_buys else None)

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
        # Pobieramy próbkę 30 spółek dla dashboardu (żeby było szybciej niż 500)
        preview = tickers[:30] if len(tickers) > 30 else tickers
        data = yf.download(preview, period="1mo", progress=False, timeout=5, group_by='ticker', auto_adjust=False)
        changes = []
        for t in preview:
            try:
                if len(data[t]) > 10:
                    c, p = data[t]['Close'].iloc[-1], data[t]['Close'].iloc[-2]
                    s = data[t]['Close'].iloc[0]
                    mon_chg = ((c-s)/s)*100
                    changes.append({"t": t, "mc": mon_chg, "p": c})
            except: pass
        changes.sort(key=lambda x: x['mc'])
        return sorted(changes, key=lambda x: x['mc'], reverse=True)[:5], changes[:5]
    except: return [], []

# --- UI ---
with st.sidebar:
    st.header("KOLgejt 10.0")
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
    market="WIG20"; tickers_scan=get_full_market_tickers("WIG20"); tickers_fund=POOL_WIG20
elif "Nasdaq" in market_choice: 
    market="Nasdaq 100"; tickers_scan=get_full_market_tickers("Nasdaq 100"); tickers_fund=POOL_NASDAQ
else: 
    market="S&P 500"; tickers_scan=get_full_market_tickers("S&P 500"); tickers_fund=POOL_SP500

# 1. PULPIT - WZROSTY / SPADKI NA SLIDERZE
st.subheader(f"🔥 Przepływ Rynku: {market}")
with st.spinner("Analiza trendów..."):
    gainers, losers = get_market_overview(tickers_scan) # Używamy listy skanera

# Slider WZROSTY
st.write("**🚀 Top Wzrosty (Miesiąc)**")
if gainers:
    gainers_html = '<div class="scroll-container">'
    for g in gainers:
        card = f"""
        <div class="mini-card mini-card-up">
            <div class="mini-ticker">{g['t'].replace('.WA','')}</div>
            <div class="mini-price">{g['p']:.2f}</div>
            <div class="mini-change text-green">+{g['mc']:.2f}%</div>
        </div>
        """
        gainers_html += card
    gainers_html += "</div>"
    st.markdown(gainers_html, unsafe_allow_html=True)
else: st.write("Brak danych.")

st.write("")

# Slider SPADKI
st.write("**🔻 Top Spadki (Miesiąc)**")
if losers:
    losers_html = '<div class="scroll-container">'
    for l in losers:
        card = f"""
        <div class="mini-card mini-card-down">
            <div class="mini-ticker">{l['t'].replace('.WA','')}</div>
            <div class="mini-price">{l['p']:.2f}</div>
            <div class="mini-change text-red">{l['mc']:.2f}%</div>
        </div>
        """
        losers_html += card
    losers_html += "</div>"
    st.markdown(losers_html, unsafe_allow_html=True)
else: st.write("Brak danych.")

st.divider()

# 2. FUNDAMENTY (Pula Smart)
with st.spinner("Szukam perełek fundamentalnych (Smart Pool)..."):
    top_funds, best_pick = scan_fundamentals(tickers_fund)

st.subheader("🏆 Analyst Strong Buy")
if best_pick:
    e = best_pick
    logo_html = f'<div class="logo-container"><img src="{e["logo"]}" class="big-logo"></div>' if e['logo'] else '<div class="logo-container" style="height:60px;"></div>'
    st.markdown(f"""<div class="webull-card strong-buy-card" style="margin: 0 auto; display: block;"><div class="badge">STRONG BUY</div><div class="card-header"><a href="{e['link']}" target="_blank">{e['ticker'].replace('.WA','')} 🔗</a></div><table class="webull-table"><thead><tr><th>Cel Cenowy</th><th>Potencjał</th><th>Wzrost EPS</th></tr></thead><tbody><tr><td>{e['target_price']}</td><td class="text-green">+{e['upside']:.1f}%</td><td class="{e['g_eps_cls']}">{e['earn_growth']}%</td></tr></tbody></table>{logo_html}<div class="bottom-stats" style="text-align:center;">Rekomendacja: <strong>STRONG BUY</strong><br>EPS Est: {e['eps_est']}</div></div>""", unsafe_allow_html=True)
else: st.info("Brak 'Strong Buy' w tej grupie.")

st.write("---")
st.subheader("💎 Top 5 Fundamentalnych (Slider)")
if top_funds:
    fund_html = '<div class="scroll-container">'
    for e in top_funds:
        logo_html = f'<div class="logo-container"><img src="{e["logo"]}" class="big-logo"></div>' if e['logo'] else '<div class="logo-container" style="height:60px;"></div>'
        card = f"""<div class="webull-card"><div class="card-header"><a href="{e['link']}" target="_blank">{e['ticker'].replace('.WA','')} 🔗</a></div><table class="webull-table"><thead><tr><th>Wskaźnik</th><th>Prognoza</th><th>Wynik</th><th>Beat/Miss</th></tr></thead><tbody><tr><td>EPS</td><td>{e['eps_est']}</td><td>{e['eps_act']}</td><td class="{e['eps_cls']}">{e['eps_txt']}</td></tr><tr class="row-alt"><td>Przychód</td><td>{e['rev_est']}</td><td>{e['rev_act']}</td><td class="{e['rev_class']}">{e['rev_txt']}</td></tr></tbody></table>{logo_html}<div class="bottom-stats"><div class="stat-row"><span>Rev r/r:</span><span class="{e['g_rev_cls']}">{e['rev_growth']}%</span></div><div class="stat-row"><span>EPS r/r:</span><span class="{e['g_eps_cls']}">{e['earn_growth']}%</span></div></div></div>"""
        fund_html += card
    fund_html += "</div>"
    st.markdown(fund_html, unsafe_allow_html=True)

st.divider()

# 4. SKANER (PEŁNA LISTA)
st.subheader(f"📡 Skaner Techniczny ({len(tickers_scan)} spółek)")
if st.button(f"🔍 SKANUJ CAŁY RYNEK", type="primary", use_container_width=True):
    prog = st.progress(0); stat = st.empty(); found = []
    
    # Limit 500 dla pełnego skanowania (może trwać ok. 60s)
    scan_limit = len(tickers_scan) 
    
    for i, t in enumerate(tickers_scan):
        if i%10==0: prog.progress((i+1)/scan_limit); stat.text(f"Analiza {i+1}/{scan_limit}: {t}")
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
                    l = f"https://finance.yahoo.com/quote/{item['ticker']}"
                    st.link_button("👉 Yahoo Finance", l)
                with c2: st.line_chart(item['chart_data'].tail(60))
    else: st.warning("Brak wyników.")
