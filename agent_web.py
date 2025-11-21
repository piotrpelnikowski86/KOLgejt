import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
import requests
import os
from io import StringIO
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="🐊", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- CSS (ZAAWANSOWANE POZYCJONOWANIE) ---
st.markdown("""
<style>
/* Kontener slidera */
.scroll-container {display: flex; overflow-x: auto; gap: 15px; padding: 15px 5px; width: 100%; scrollbar-width: thin; scrollbar-color: #555 #1E1E1E;}

/* Bazowa karta */
.webull-card {flex: 0 0 auto; background-color: #262730; border-radius: 12px; border: 1px solid #41424C; overflow: visible; position: relative;}

/* Mniejsza karta dla slidera */
.slider-card {width: 250px; font-size: 11px;}

/* Wrapper centrujący kartę Strong Buy i pozycjonujący krokodyla */
.strong-buy-wrapper {
    position: relative;
    width: 320px; /* Szerokość głównej karty */
    margin: 30px auto; /* Centrowanie na stronie */
}

/* Styl głównej karty Strong Buy */
.strong-buy-card-style {
    width: 100%; 
    border: 2px solid #FFD700;
    box-shadow: 0 0 25px rgba(255, 215, 0, 0.4);
    z-index: 2; 
    background-color: #262730;
    border-radius: 12px;
}

/* Absolutnie pozycjonowany krokodyl */
.croc-absolute {
    position: absolute;
    bottom: -15px; 
    left: -100px;   
    width: 150px;  
    height: auto;
    z-index: 3; 
    filter: drop-shadow(3px 3px 5px rgba(0,0,0,0.5)); 
    pointer-events: none;
}

/* Pozostałe style */
.mini-card {flex: 0 0 auto; background-color: #1E1E1E; border-radius: 8px; width: 160px; padding: 10px; text-align: center; border: 1px solid #333; box-shadow: 0 2px 5px rgba(0,0,0,0.3); transition: transform 0.2s;}
.mini-card:hover {transform: scale(1.03); border-color: #555;}
.mini-card-up {border-top: 3px solid #00FF00;}
.mini-card-down {border-top: 3px solid #FF4B4B;}
.mini-ticker {font-size: 16px; font-weight: bold; color: white; margin-bottom: 5px;}
.mini-price {font-size: 14px; color: #CCC;}
.mini-change {font-size: 14px; font-weight: bold; margin-top: 2px;}
.badge {position: absolute; top: 10px; right: 10px; background-color: #FFD700; color: black; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; z-index: 10;}
.card-header {text-align: center; padding: 12px; background-color: #0E1117; border-bottom: 1px solid #41424C; border-top-left-radius: 12px; border-top-right-radius: 12px;}
.card-header a {color: white; font-size: 18px; font-weight: bold; text-decoration: none;}
.webull-table {width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; color: #DDD;}
.webull-table th {background-color: #31333F; color: #AAA; padding: 6px; font-weight: normal;}
.webull-table td {padding: 8px 4px; border-bottom: 1px solid #31333F;}
.row-alt {background-color: #2C2D36;}
.text-green {color: #00FF00; font-weight: bold;}
.text-red {color: #FF4B4B; font-weight: bold;}
.logo-container {display: flex; justify-content: center; align-items: center; padding: 15px; background-color: #262730; min-height: 70px;}
.big-logo {height: 50px; width: 50px; object-fit: contain; border-radius: 8px; background-color: white; padding: 4px;}
.bottom-stats {padding: 10px; font-size: 11px; background-color: #1E1E1E; color: #CCC; border-top: 1px solid #41424C; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;}
.stat-row {display: flex; justify-content: space-between; margin-bottom: 4px;}
.mini-link {text-decoration: none; color: inherit; display: block;}
.info-box {background-color: #262730; padding: 12px; border-left: 3px solid #00AAFF; border-radius: 5px; margin-bottom: 15px; font-size: 13px; line-height: 1.4;}
.info-title {font-weight: bold; color: #00AAFF; margin-bottom: 5px; display: block;}
/* Centrowanie kolumn */
[data-testid="column"] { display: flex; align-items: center; justify-content: center; }
</style>
""", unsafe_allow_html=True)

# --- LISTY ---
POOL_SP500 = ["NVDA", "META", "AMD", "AMZN", "MSFT", "GOOGL", "AAPL", "TSLA", "NFLX", "AVGO", "LLY", "JPM", "V", "MA", "COST", "PEP", "KO", "XOM", "CVX", "BRK-B", "DIS", "WMT", "HD", "PG", "MRK", "ABBV", "CRM", "ACN", "LIN", "ADBE"]
POOL_NASDAQ = ["NVDA", "META", "AMD", "AMZN", "MSFT", "GOOGL", "AAPL", "TSLA", "NFLX", "AVGO", "COST", "PEP", "INTC", "CSCO", "TMUS", "CMCSA", "AMGN", "TXN", "QCOM", "HON", "INTU", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADP", "LRCX"]
POOL_GPW = ["PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA", "CDR.WA", "SPL.WA", "CPS.WA", "PGE.WA", "KRU.WA", "KTY.WA", "ACP.WA", "MBK.WA", "JSW.WA", "ALR.WA", "TPE.WA", "CCC.WA", "XTB.WA", "ENA.WA", "MIL.WA", "BHW.WA", "ING.WA", "KRY.WA", "BDX.WA", "TEN.WA", "11B.WA", "TXT.WA", "GPP.WA", "APR.WA", "ASB.WA", "BMC.WA", "CIG.WA", "DAT.WA", "DOM.WA", "EAT.WA", "EUR.WA", "GPW.WA", "GTN.WA", "HUG.WA", "KER.WA", "LWB.WA", "MAB.WA", "MBR.WA", "MDG.WA", "MRC.WA", "NEU.WA", "OAT.WA", "PCR.WA", "PEP.WA", "PKP.WA", "PLW.WA", "RBW.WA", "RVU.WA", "SLV.WA", "STP.WA", "TOR.WA", "VGO.WA", "WPL.WA"]
BACKUP_NASDAQ = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP", "AMD", "NFLX", "CSCO", "INTC", "TMUS", "CMCSA", "TXN", "AMAT", "QCOM", "HON", "INTU", "AMGN", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADP", "LRCX", "ADI", "REGN", "VRTX", "MU", "PANW", "SNPS", "KLAC", "CDNS", "CHTR", "MELI", "MAR", "CSX", "PYPL", "MNST", "ORLY", "ASML", "NXPI", "CTAS", "WDAY", "FTNT", "KDP"]

DOMAINS = {"AAPL": "apple.com", "MSFT": "microsoft.com", "NVDA": "nvidia.com", "GOOGL": "google.com", "AMZN": "amazon.com", "META": "meta.com", "TSLA": "tesla.com", "AMD": "amd.com", "NFLX": "netflix.com", "JPM": "jpmorganchase.com", "DIS": "disney.com", "AVGO": "broadcom.com", "PKN.WA": "orlen.pl", "PKO.WA": "pkobp.pl", "PZU.WA": "pzu.pl", "PEO.WA": "pekao.com.pl", "DNP.WA": "grupadino.pl", "KGH.WA": "kghm.com", "LPP.WA": "lpp.com", "ALE.WA": "allegro.eu", "CDR.WA": "cdprojekt.com", "SPL.WA": "santander.pl", "CPS.WA": "cyfrowypolsat.pl", "PGE.WA": "gkpge.pl", "CCC.WA": "ccc.eu", "XTB.WA": "xtb.com", "ING.WA": "ing.pl", "MBK.WA": "mbank.pl", "ALR.WA": "aliorbank.pl", "TPE.WA": "tauron.pl", "JSW.WA": "jsw.pl"}

def format_large_num(num):
    if num is None: return "-"
    if num > 1e9: return f"{num/1e9:.2f}B"
    if num > 1e6: return f"{num/1e6:.2f}M"
    return f"{num:.2f}"

@st.cache_data(ttl=3600)
def get_full_tickers_v11(market):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if market == "GPW":
