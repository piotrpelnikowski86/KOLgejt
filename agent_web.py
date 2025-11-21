import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="📈", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- LISTY SPÓŁEK (STABILNE) ---

SP500_TOP = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "LLY", "AVGO",
    "JPM", "V", "XOM", "UNH", "MA", "PG", "JNJ", "HD", "MRK", "COST",
    "ABBV", "CVX", "CRM", "BAC", "WMT", "AMD", "ACN", "PEP", "KO", "LIN",
    "TMO", "DIS", "MCD", "CSCO", "ABT", "INTC", "WFC", "VZ", "NFLX", "QCOM",
    "INTU", "NKE", "IBM", "PM", "GE", "AMAT", "TXN", "NOW", "SPGI", "CAT"
]

NASDAQ_TOP = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP",
    "AMD", "NFLX", "CSCO", "INTC", "TMUS", "CMCSA", "TXN", "AMAT", "QCOM", "HON",
    "INTU", "AMGN", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADP", "LRCX", "ADI",
    "REGN", "VRTX", "MU", "PANW", "SNPS", "KLAC", "CDNS", "CHTR", "MELI", "MAR",
    "CSX", "PYPL", "MNST", "ORLY", "ASML", "NXPI", "CTAS", "WDAY", "FTNT", "KDP"
]

WIG20_FULL = [
    "PKN.WA", "PKO.WA", "PZU.WA", "PEO.WA", "DNP.WA", "KGH.WA", "LPP.WA", "ALE.WA",
    "
