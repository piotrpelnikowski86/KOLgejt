import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO
import warnings

# --- KONFIGURACJA ---
st.set_page_config(page_title="KOLgejt", page_icon="⚙️", layout="wide")
warnings.simplefilter(action='ignore', category=FutureWarning)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

# --- FUNKCJE MATEMATYCZNE ---

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_sma(series, period):
    return series.rolling(window=period).mean()

def calc_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, lower

# --- POBIERANIE DANYCH ---

@st.cache_data(ttl=24*3600)
def get_tickers(market_type):
    headers = {"User-Agent": "Mozilla/5.0"}
    tickers = []
    
    if market_type == "Nasdaq":
        url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        try:
            tables = pd.read_html(requests.get(url, headers=headers).text)
            for t in tables:
                if 'Ticker' in t.columns: 
                    tickers = t['Ticker'].tolist()
                    break
            if not tickers: tickers = tables[4]['Ticker'].tolist()
        except:
            return ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]
    else:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        try:
            tables = pd.read_html(requests.get(url, headers=headers).text)
            tickers = tables[0]['Symbol'].tolist()
        except:
            return ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
            
    return [str(t).replace('.', '-') for t in tickers]

# --- GŁÓWNA FUNKCJA ANALIZY ---

def analyze_stock(ticker, strategy, params):
    try:
        # Pobieramy więcej danych (2 lata) dla długich średnich
        data = yf.download(ticker, period="2y", progress=False, timeout=5, auto_adjust=False)
        if len(data) < 200: return None

        close = data['Close']
        
        # Obliczamy wskaźniki w zależności od wybranej strategii
        result = None
        chart_lines = {}

        # === STRATEGIA 1: RSI ODBICIE ===
        if strategy == "RSI":
            rsi_val = calc_rsi(close, 14)
            threshold = params['rsi_threshold']
            
            # Warunek: RSI było poniżej progu, a teraz jest powyżej (lub po prostu jest niskie)
            current_rsi = rsi_val.iloc[-1]
            prev_rsi = rsi_val.iloc[-2]
            
            if current_rsi < threshold + 5: # Szersze spektrum dla obserwacji
                is_signal = (prev_rsi <= threshold and current_rsi > threshold) or (current_rsi <= threshold)
                
                if is_signal:
                    result = {
                        "info": f"RSI: {round(current_rsi, 1)} (Próg: {threshold})",
                        "metric_val": round(current_rsi, 1),
                        "metric_name": "RSI"
                    }
                    chart_lines = {'RSI': rsi_val}

        # === STRATEGIA 2: TREND (SMA) ===
        elif strategy == "SMA":
            period = params['sma_period']
            sma = calc_sma(close, period)
            current_price = close.iloc[-1]
            current_sma = sma.iloc[-1]
            
            # Warunek: Cena powyżej średniej
            if current_price > current_sma:
                dist = (current_price - current_sma) / current_sma * 100
                result = {
                    "info": f"Cena {round(dist, 1)}% powyżej SMA{period}",
                    "metric_val": round(current_sma, 2),
                    "metric_name": f"SMA {period}"
                }
                chart_lines = {f'SMA_{period}': sma}

        # === STRATEGIA 3: BOLLINGER BANDS ===
        elif strategy == "Bollinger":
            up, low = calc_bollinger(close, 20, 2)
            current_price = close.iloc[-1]
            current_low = low.iloc[-1]
            
            # Warunek: Cena blisko dolnej wstęgi lub ją przebiła
            if current_price <= current_low * 1.02: # 2% marginesu błędu
                result = {
                    "info": "Cena przy dolnej wstędze (Okazja?)",
                    "metric_val": round(current_low, 2),
                    "metric_name": "Dolna Wstęga"
                }
                chart_lines = {'Lower_Band': low, 'Upper_Band': up}

        if result:
            return {
                "ticker": ticker,
                "price": round(close.iloc[-1], 2),
                "details": result,
                "chart_data": data[['Close']].copy(),
                "extra_lines": chart_lines
            }

    except:
        return None
    return None

# --- INTERFEJS ---

st.title("⚙️ KOLgejt 4.0")

# --- SIDEBAR (KONFIGURACJA) ---
with st.sidebar:
    st.header("🎛️ Panel Sterowania")
    
    st.subheader("1. Rynek")
    market = st.radio("Wybierz indeks:", ["S&P 500", "Nasdaq"], label_visibility="collapsed")
    
    st.subheader("2. Strategia")
    strategy_type = st.selectbox(
        "Czego szukamy?",
        ["RSI", "SMA", "Bollinger"],
        format_func=lambda x: {
            "RSI": "🏄 Odbicie (RSI)",
            "SMA": "📈 Silny Trend (SMA)",
            "Bollinger": "🎯 Wstęgi Bollingera"
        }[x]
    )
    
    # Dynamiczne suwaki w zależności od strategii
    params = {}
    st.write("---")
    st.write("**Parametry Strategii:**")
    
    if strategy_type == "RSI":
        params['rsi_threshold'] = st.slider("Próg wyprzedania RSI (Taniej niż...)", 20, 50, 35)
        st.caption("Im niższa wartość, tym silniej wyprzedana musi być spółka.")
        
    elif strategy_type == "SMA":
        params['sma_period'] = st.slider("Długość średniej (Dni)", 10, 200, 50, step=10)
        st.caption("50 = trend średni, 200 = trend długi.")
        
    elif strategy_type == "Bollinger":
        st.info("Szukamy spółek, które dotknęły dolnej wstęgi (statystycznie tanie).")

# --- GŁÓWNA CZĘŚĆ ---

tab1, tab2 = st.tabs(["📡 Skaner", "⭐ Obserwowane"])

with tab1:
    st.write(f"**Aktywna strategia:** {strategy_type} na rynku {market}")
    
    if st.button("🔍 URUCHOM SKANER", type="primary", use_container_width=True):
        tickers = get_tickers(market)
        
        if not tickers:
            st.error("Błąd pobierania listy spółek.")
        else:
            progress = st.progress(0)
            status = st.empty()
            found = []
            
            for i, t in enumerate(tickers):
                if i % 10 == 0: 
                    progress.progress((i+1)/len(tickers))
                    status.text(f"Analizuję: {t}")
                
                res = analyze_stock(t, strategy_type, params)
                if res: found.append(res)
            
            progress.empty()
            status.empty()
            
            if found:
                st.success(f"Znaleziono {len(found)} sygnałów!")
                for item in found:
                    with st.expander(f"🔥 {item['ticker']} - {item['price']}$", expanded=True):
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.write(f"**{item['details']['info']}**")
                            st.metric(item['details']['metric_name'], item['details']['metric_val'])
                            
                            # Przycisk dodawania do obserwowanych
                            if st.button(f"⭐ Dodaj {item['ticker']}", key=f"add_{item['ticker']}"):
                                if item['ticker'] not in st.session_state.watchlist:
                                    st.session_state.watchlist.append(item['ticker'])
                                    st.toast("Dodano!")

                            st.link_button("Yahoo Finance", f"https://finance.yahoo.com/quote/{item['ticker']}")
                        
                        with c2:
                            # Rysowanie wykresu z dodatkowymi liniami (wskaźnikami)
                            chart = item['chart_data'].tail(100)
                            for name, line in item['extra_lines'].items():
                                chart[name] = line
                            
                            colors = ["#0000FF"] # Cena (Niebieski)
                            if len(chart.columns) > 1: colors.append("#FF0000") # Wskaźnik 1 (Czerwony)
                            if len(chart.columns) > 2: colors.append("#00FF00") # Wskaźnik 2 (Zielony)
                            
                            st.line_chart(chart, color=colors)
            else:
                st.warning("Brak wyników. Spróbuj poluzować kryteria w panelu bocznym (z lewej).")

with tab2:
    st.subheader("Obserwowane")
    new = st.text_input("Dodaj symbol:", placeholder="np. AMD").upper().strip()
    if st.button("Dodaj") and new:
        if new not in st.session_state.watchlist:
            st.session_state.watchlist.append(new)
            st.rerun()
            
    if st.session_state.watchlist:
        if st.button("Wyczyść"):
            st.session_state.watchlist = []
            st.rerun()
            
        for w in st.session_state.watchlist:
            st.write(f"⭐ **{w}**")
    else:
        st.info("Lista pusta.")
