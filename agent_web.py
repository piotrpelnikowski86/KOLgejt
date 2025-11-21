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
    border-bottom: 1px solid #41424C;
}
.card-header a {
    color: white;
    font-size: 18px;
    font-weight: bold;
    text-decoration: none;
    transition: color 0.3s;
}
.card-header a:hover {
    color: #00AAFF;
    text-decoration: underline;
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
    min-height: 80px;
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
    color: #CCC
