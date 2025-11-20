import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import warnings

# --- KONFIGURACJA ---
# Pamiętaj: jeśli masz logo.jpeg, zmień ikonę poniżej. Jeśli nie, zostaw emotikonę.
st.set_page_config(page_title="KOLgejt 2.0", page_icon="📈", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- FUNKCJE MATEMATYCZNE (Ręczne, niezawodne) ---

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_sma(series, period=20):
    return series.rolling(window=period).mean()

# --- POBIERANIE LIST SPÓŁEK ---

@st.cache_data(ttl=24*3600)
def get_sp500_tickers():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    try:
        tables = pd.read_html(url)
        tickers = tables[0]['Symbol'].tolist()
        return [str(t).replace('.', '-') for t in tickers]
    except:
        return []

@st.cache_data(ttl=24*3600)
def get_nasdaq100_tickers():
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    try:
        tables = pd.read_html(url)
        # Szukamy tabeli z tickerami (czasem jest to tabela nr 4)
        for table in tables:
            if 'Ticker' in table.columns:
                return [str(t).replace('.', '-') for t in table['Ticker'].tolist()]
        return tables[4]['Ticker'].tolist()
    except:
        return []

# --- ANALIZA ---

def analyze_stock(ticker):
    try:
        # Pobieramy 6 miesięcy danych, żeby narysować ładny wykres
        data = yf.download(ticker, period="6mo", progress=False, timeout=5, auto_adjust=False)
        
        if len(data) < 25: return None

        # Obliczenia
        data['RSI_14'] = calculate_rsi(data['Close'], 14)
        data['SMA_20'] = calculate_sma(data['Close'], 20)
        data['vol_sma'] = calculate_sma(data['Volume'], 20)
        
        # Kopia danych do wykresu (zanim usuniemy puste wiersze potrzebne do obliczeń)
        chart_data = data[['Close', 'SMA_20']].copy()
        
        data.dropna(inplace=True)
        if len(data) < 2: return None

        last = data.iloc[-1]
        prev = data.iloc[-2]

        # WARUNKI STRATEGII
        # 1. RSI odbija od dna (było <= 35, jest > 35)
        c1 = prev['RSI_14'] <= 35 and last['RSI_14'] > 35
        # 2. Cena powyżej średniej
        c2 = last['Close'] > last['SMA_20']
        # 3. Wolumen większy niż średnia
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

# --- INTERFEJS APLIKACJI ---

st.title("📈 KOLgejt 2.0")
st.markdown("### Centrum dowodzenia inwestora")

# PANEL BOCZNY (Sidebar)
with st.sidebar:
    st.header("⚙️ Ustawienia")
    wybor_rynku = st.radio(
        "Wybierz rynek:",
        ["🇺🇸 S&P 500 (Stabilne)", "💻 Nasdaq 100 (Technologie)"]
    )
    st.info("Wskazówka: Nasdaq jest bardziej dynamiczny i może dawać więcej sygnałów.")

# PRZYCISK START
if st.button("🔍 URUCHOM SKANER", type="primary"):
    
    if "Nasdaq" in wybor_rynku:
        tickers = get_nasdaq100_tickers()
        st.toast(f"Wybrano Nasdaq 100. Skanuję {len(tickers)} spółek...")
    else:
        tickers = get_sp500_tickers()
        st.toast(f"Wybrano S&P 500. Skanuję {len(tickers)} spółek...")

    if not tickers:
        st.error("Błąd: Nie udało się pobrać listy spółek z Wikipedii.")
    else:
        bar = st.progress(0)
        status = st.empty()
        okazje = []
        
        # Pętla skanowania
        for i, t in enumerate(tickers):
            # Aktualizacja paska co 5% żeby nie zamulać
            if i % 5 == 0 or i == len(tickers) - 1:
                bar.progress((i + 1) / len(tickers))
                status.text(f"Analizuję: {t}")
            
            wynik = analyze_stock(t)
            if wynik:
                okazje.append(wynik)
        
        status.text("Analiza zakończona!")
        bar.empty()
        st.divider()

        # WYNIKI
        if okazje:
            st.success(f"✅ Znaleziono {len(okazje)} sygnałów kupna!")
            
            for item in okazje:
                # Tworzymy ładny kontener dla każdej spółki
                with st.expander(f"🔥 {item['ticker']} - Cena: {item['price']} $", expanded=True):
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.metric("RSI (Momentum)", item['rsi'])
                        st.metric("Wolumen", f"{item['vol_ratio']}x normy")
                        
                        # Link do Yahoo Finance
                        link = f"https://finance.yahoo.com/quote/{item['ticker']}"
                        st.link_button("👉 Zobacz na Yahoo Finance", link)
                    
                    with col2:
                        st.write("📉 Wykres (Cena vs Średnia SMA20)")
                        # Rysujemy wykres (Cena = niebieski, Średnia = czerwony)
                        st.line_chart(
                            item['chart_data'].tail(60),
                            color=["#0000FF", "#FF0000"] 
                        )
        else:
            st.warning("Brak sygnałów spełniających kryteria na wybranym rynku.")
