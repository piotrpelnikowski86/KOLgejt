import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO
import warnings

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="IMG_4485.jpeg")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- FUNKCJE MATEMATYCZNE (Ręczne obliczenia zamiast biblioteki) ---

def calculate_rsi(series, period=14):
    """Oblicza RSI ręcznie, bez użycia zewnętrznych bibliotek."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_sma(series, period=20):
    """Oblicza średnią kroczącą."""
    return series.rolling(window=period).mean()

# --- FUNKCJE GŁÓWNE ---

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
            # Backup GitHub
            url_csv = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
            target_table = pd.read_csv(url_csv)
        
        tickers = target_table['Symbol'].tolist()
        return [str(t).replace('.', '-') for t in tickers]
    except Exception as e:
        st.error(f"Błąd listy spółek: {e}")
        return []

def analyze_stock(ticker):
    try:
        # Pobieranie danych (z wyłączonym auto_adjust dla bezpieczeństwa)
        data = yf.download(ticker, period="1y", progress=False, timeout=5, auto_adjust=False)
        
        if len(data) < 25: return None # Potrzebujemy min. 25 dni do obliczeń

        # --- RĘCZNE OBLICZENIA ---
        # Zamiast data.ta.rsi używamy naszej funkcji
        data['RSI_14'] = calculate_rsi(data['Close'], 14)
        data['SMA_20'] = calculate_sma(data['Close'], 20)
        data['vol_sma'] = calculate_sma(data['Volume'], 20)
        
        data.dropna(inplace=True)
        if len(data) < 2: return None

        last = data.iloc[-1]
        prev = data.iloc[-2]

        # --- LOGIKA STRATEGII ---
        # 1. RSI odbija od dna (przebija 35 w górę)
        c1 = prev['RSI_14'] <= 35 and last['RSI_14'] > 35
        # 2. Cena powyżej średniej
        c2 = last['Close'] > last['SMA_20']
        # 3. Wolumen wyższy niż średnia
        c3 = last['Volume'] > (last['vol_sma'] * 1.2)

        if c1 and c2 and c3:
            return {
                "Spółka": ticker,
                "Cena": round(last['Close'], 2),
                "RSI": round(last['RSI_14'], 2),
                "Wolumen x": round(last['Volume'] / last['vol_sma'], 1)
            }
    except:
        return None
    return None

# --- INTERFEJS ---

st.title("📈 KOLgejt")
st.write("Mobilny skaner giełdowy (S&P 500).")

if st.button("🔍 URUCHOM SKANOWANIE"):
    tickers = get_sp500_tickers()
    
    if not tickers:
        st.error("Błąd połączenia z Wikipedią.")
    else:
        st.info(f"Analizuję {len(tickers)} spółek...")
        bar = st.progress(0)
        status = st.empty()
        okazje = []
        
        for i, t in enumerate(tickers):
            bar.progress((i + 1) / len(tickers))
            status.text(f"Sprawdzam: {t}")
            
            wynik = analyze_stock(t)
            if wynik:
                okazje.append(wynik)
                st.toast(f"🔥 OKAZJA: {t}")
        
        status.text("Gotowe!")
        bar.empty()
        
        st.divider()
        if okazje:
            st.success(f"Znaleziono {len(okazje)} sygnałów!")
            st.dataframe(pd.DataFrame(okazje), use_container_width=True)
            st.balloons()
        else:
            st.warning("Brak sygnałów spełniających kryteria.")


