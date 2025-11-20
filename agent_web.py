import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO
import warnings

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt 2.0", page_icon="📈")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- FUNKCJE MATEMATYCZNE ---

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_sma(series, period=20):
    return series.rolling(window=period).mean()

# --- POBIERANIE DANYCH (PANCERNE) ---

@st.cache_data(ttl=24*3600)
def get_sp500_tickers():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers)
        tables = pd.read_html(StringIO(response.text))
        tickers = tables[0]['Symbol'].tolist()
        return [str(t).replace('.', '-') for t in tickers]
    except:
        try:
            backup_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
            backup_data = pd.read_csv(backup_url)
            tickers = backup_data['Symbol'].tolist()
            return [str(t).replace('.', '-') for t in tickers]
        except:
            return []

@st.cache_data(ttl=24*3600)
def get_nasdaq100_tickers():
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers)
        tables = pd.read_html(StringIO(response.text))
        for table in tables:
            if 'Ticker' in table.columns:
                return [str(t).replace('.', '-') for t in table['Ticker'].tolist()]
        return [str(t).replace('.', '-') for t in tables[4]['Ticker'].tolist()]
    except:
        return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX"]

# --- ANALIZA ---

def analyze_stock(ticker):
    try:
        data = yf.download(ticker, period="6mo", progress=False, timeout=10, auto_adjust=False)
        if len(data) < 25: return None

        data['RSI_14'] = calculate_rsi(data['Close'], 14)
        data['SMA_20'] = calculate_sma(data['Close'], 20)
        data['vol_sma'] = calculate_sma(data['Volume'], 20)
        
        chart_data = data[['Close', 'SMA_20']].copy()
        
        data.dropna(inplace=True)
        if len(data) < 2: return None

        last = data.iloc[-1]
        prev = data.iloc[-2]

        c1 = prev['RSI_14'] <= 35 and last['RSI_14'] > 35
        c2 = last['Close'] > last['SMA_20']
        c3 = last['Volume'] > (last['vol_sma'] * 1.2)

        if c1 and c2 and c3:
            return {
                "ticker": ticker,
                "price": round(last['Close'], 2),
                "rsi": round(last['RSI_14'], 2),
                "vol_ratio": round(last['Volume'] / last['vol_sma'], 1),
                "chart_data": chart_data
            }
    except:
        return None
    return None

# --- INTERFEJS (NOWY UKŁAD) ---

st.title("📈 KOLgejt 2.0")
st.markdown("### Centrum dowodzenia inwestora")

st.divider() # Linia oddzielająca

# WYBÓR RYNKU (TERAZ JEST NAD PRZYCISKIEM)
st.write("**Wybierz rynek do analizy:**")
wybor_rynku = st.radio(
    "Rynek", # Etykieta (ukryta przez label_visibility, jeśli chcesz)
    ["🇺🇸 S&P 500 (Stabilne)", "💻 Nasdaq 100 (Technologie)"],
    horizontal=True, # Ustawienie poziome - wygląda lepiej na telefonie
    label_visibility="collapsed" # Ukrywamy mały napis "Rynek" bo mamy nagłówek wyżej
)

st.write("") # Mały odstęp

# PRZYCISK START (SZEROKI)
if st.button("🔍 URUCHOM SKANER", type="primary", use_container_width=True):
    
    if "Nasdaq" in wybor_rynku:
        tickers = get_nasdaq100_tickers()
        rynek_nazwa = "Nasdaq 100"
    else:
        tickers = get_sp500_tickers()
        rynek_nazwa = "S&P 500"

    if not tickers:
        st.error(f"Błąd: Nie udało się pobrać listy spółek dla {rynek_nazwa}.")
    else:
        st.toast(f"Skanuję {rynek_nazwa} ({len(tickers)} spółek)...")
        
        bar = st.progress(0)
        status = st.empty()
        okazje = []
        
        for i, t in enumerate(tickers):
            if i % 5 == 0 or i == len(tickers) - 1:
                bar.progress((i + 1) / len(tickers))
                status.text(f"Analizuję: {t}")
            
            wynik = analyze_stock(t)
            if wynik:
                okazje.append(wynik)
        
        status.text("Analiza zakończona!")
        bar.empty()
        
        if okazje:
            st.success(f"✅ Znaleziono {len(okazje)} sygnałów kupna!")
            for item in okazje:
                with st.expander(f"🔥 {item['ticker']} - Cena: {item['price']} $", expanded=True):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.metric("RSI", item['rsi'])
                        st.metric("Wolumen", f"{item['vol_ratio']}x normy")
                        link = f"https://finance.yahoo.com/quote/{item['ticker']}"
                        st.link_button("👉 Yahoo Finance", link)
                    with col2:
                        st.write("📉 Wykres vs SMA20")
                        st.line_chart(item['chart_data'].tail(60), color=["#0000FF", "#FF0000"])
        else:
            st.warning("Brak sygnałów spełniających kryteria na wybranym rynku.")
