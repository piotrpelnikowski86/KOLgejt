import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="📈", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- CSS (STYL WEBULL DARK) ---
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
    color: white;
    font-size: 18px;
    font-weight: bold;
    border-bottom: 1px solid #41424C;
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
WIG20_FULL = ["PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA", "CDR.WA"]

DOMAINS = {
    "AAPL": "apple.com", "MSFT": "microsoft.com", "NVDA": "nvidia.com", "GOOGL": "google.com",
    "AMZN": "amazon.com", "META": "meta.com", "TSLA": "tesla.com", "AMD": "amd.com",
    "NFLX": "netflix.com", "PKN.WA": "orlen.pl", "PKO.WA": "pkobp.pl", "CDR.WA": "cdprojekt.com"
}

def format_large_num(num):
    if num is None: return "-"
    if num > 1e9: return f"{num/1e9:.2f}B"
    if num > 1e6: return f"{num/1e6:.2f}M"
    return f"{num:.2f}"

@st.cache_data(ttl=3600*12)
def get_earnings_data_v4(ticker):
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
        
        logo = f"https://logo.clearbit.com/{DOMAINS.get(ticker, 'google.com')}"
        
        return {
            "ticker": ticker,
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
