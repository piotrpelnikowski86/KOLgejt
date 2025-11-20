import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from io import StringIO
import warnings

# 1. Konfiguracja strony
st.set_page_config(page_title="KOLgejt", page_icon="📈")
warnings.simplefilter(action='ignore', category=FutureWarning)

# 2. Funkcje (mózg programu)
@st.cache_data(ttl=24*3600)
def get_sp500_tickers():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers)
        tables = pd.read_html(StringIO(response.text))
        target_table = None
        for table in tables:
            if 'Symbol' in table.columns and 'Security' in table.columns:
                target_table = table
                break
        if target_table is None:
            url_csv = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
            target_table = pd.read_csv(url_csv)
        tickers = target_table['Symbol'].tolist()
        return [str(t).replace('.', '-') for t in tickers]
    except Exception as e:
        st.error(f"Błąd: {e}")
        return []

def analyze_stock(ticker):
    try:
        # Pobieranie danych
        data = yf.download(ticker, period="1y", progress=False, timeout=5, auto_adjust=False)
        if len(data) < 21: return None

        # Obliczenia
        data.ta.rsi(length=14, append=True)
        data.ta.sma(length=20, append=True)
        data['volume_sma_20'] = data['Volume'].rolling(window=20).mean()
        data.dropna(inplace=True)
        
        if len(data) < 2: return None

        last = data.iloc[-1]
        prev = data.iloc[-2]

        # Warunki strategii
        c1 = prev['RSI_14'] <= 35 and last['RSI_14'] > 35
        c2 = last['Close'] > last['SMA_20']
        c3 = last['Volume'] > (last['volume_sma_20'] * 1.2)

        if c1 and c2 and c3:
            return {
                "Spółka": ticker,
                "Cena": round(last['Close'], 2),
                "RSI": round(last['RSI_14'], 2),
                "Wolumen x": round(last['Volume'] / last['volume_sma_20'], 1)
            }
    except:
        return None
    return None

# 3. Wygląd aplikacji (Interfejs)
st.title("📈 KOLgejt")
st.write("Twój osobisty skaner giełdowy.")

if st.button("🔍 URUCHOM KOLgejt"):
    # Tu były błędy wcięć - teraz jest poprawnie (wszystko poniżej jest przesunięte)
    tickers = get_sp500_tickers()
    
    if not tickers:
        st.error("Błąd listy spółek.")
    else:
        st.info(f"KOLgejt skanuje {len(tickers)} spółek...")
        bar = st.progress(0)
        status = st.empty()
        okazje = []
        
        for i, t in enumerate(tickers):
            bar.progress((i + 1) / len(tickers))
            status.text(f"Analiza: {t}")
            wynik = analyze_stock(t)
            if wynik:
                okazje.append(wynik)
                st.toast(f"Znaleziono: {t}")
        
        status.text("Gotowe!")
        bar.empty()
        
        if okazje:
            st.success(f"Znaleziono {len(okazje)} sygnałów!")
            st.dataframe(pd.DataFrame(okazje), use_container_width=True)
        else:
            st.warning("Brak sygnałów na dziś.")