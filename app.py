.env(file)
CRYPTOCOMPARE_API_KEY=e196fc622d38f6be3ab2e6474eea532e9187d2b7>
LIVECOINWATCH_API_KEY=5dfb79d6-82ba-4e2e-98db-4413a147327a
COOKIES_PASSWORD=Kaijasper723Avcvk64

requirements.txt(file)

streamlit
pandas
numpy
matplotlib
plotly
Pillow
scikit-learn
scipy
requests
altair
cachetools
click
pytz
tenacity
pyarrow


app.py(file)

import os
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager
import json
from PIL import Image
import qrcode

# Load environment variables
load_dotenv()

CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY")

# Initialize cookies
cookies = EncryptedCookieManager(prefix="crypto_app")
if not cookies.ready():
    st.stop()

# Token List (Your Tokens Included)
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    "Floki Inu": "floki-inu",
    "Baby Doge": "baby-doge-coin",
    "Kishu Inu": "kishu-inu",
    "Saitama": "saitama",
    "SafeMoon": "safemoon",
    "EverGrow Coin": "evergrow-coin",
    "Akita Inu": "akita-inu",
    "Volt Inu": "volt-inu",
    "CateCoin": "catecoin",
    "Shiba Predator": "shiba-predator",
    "DogeBonk": "dogebonk",
    "Flokinomics": "flokinomics",
    "StarLink": "starlink",
    "Elon Musk Coin": "elon-musk-coin",
    "DogeGF": "dogegf",
    "Ryoshi Vision": "ryoshi-vision",
    "Shibaverse": "shibaverse",
    "FEG Token": "feg-token",
    "Dogelon Mars": "dogelon-mars",
    "BabyFloki": "babyfloki",
    "PolyDoge": "polydoge",
    "TAMA": "tamadoge",
    "SpookyShiba": "spookyshiba",
    "Moonriver": "moonriver",
    "MetaHero": "metahero",
    "BabyDogeZilla": "babydogezilla",
    "NanoDogeCoin": "nanodogecoin",
    "BabyShark": "babyshark",
    "Wakanda Inu": "wakanda-inu",
    "King Shiba": "king-shiba",
    "PepeCoin": "pepecoin",
    "Pitbull": "pitbull",
    "MoonDoge": "moondoge",
    "CryptoZilla": "cryptozilla",
    "MiniDoge": "minidoge",
    "ZillaDoge": "zilladoge",
    "DogeFloki": "dogefloki",
    "Bonfida": "bonfida"
}

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("portfolio.db")
    c = conn.cursor()
    try:
        c.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                token TEXT PRIMARY KEY,
                quantity REAL,
                value REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                token TEXT PRIMARY KEY
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database Error: {e}")
    return conn, c

# Fetch token price (Dummy for simplicity, replace with API logic)
def fetch_price(token_id):
    return {"price": 1.23}  # Replace with real API logic

# Display Portfolio
def display_portfolio(c):
    c.execute("SELECT * FROM portfolio")
    data = c.fetchall()
    if not data:
        st.write("Your portfolio is empty!")
        return
    df = pd.DataFrame(data, columns=["Token", "Quantity", "Value"])
    st.write("### Your Portfolio")
    st.write(df)

# Manage Watchlist
def manage_watchlist(c, conn):
    st.write("### Manage Watchlist")
    token = st.selectbox("Add/Remove Token", list(TOKENS.keys()))
    if st.button("Add to Watchlist"):
        c.execute("INSERT OR IGNORE INTO watchlist (token) VALUES (?)", (token,))
        conn.commit()
        st.success(f"{token} added to watchlist!")
    st.write("Your Watchlist:")
    c.execute("SELECT token FROM watchlist")
    st.write(c.fetchall())

# Save Portfolio
def save_portfolio(portfolio_data):
    st.write("### Save Portfolio")
    col1, col2 = st.columns(2)
    with col1:
        # Save as file
        if st.button("Download Portfolio"):
            st.download_button(
                label="Download Portfolio",
                data=json.dumps(portfolio_data),
                file_name="portfolio.json",
                mime="application/json"
            )
    with col2:
        # Save to cookies
        if st.button("Save to Cookies"):
            cookies["portfolio"] = json.dumps(portfolio_data)
            cookies.save()
            st.success("Portfolio saved to cookies!")

# Load Portfolio
def load_portfolio():
    st.write("### Load Portfolio")
    col1, col2 = st.columns(2)
    portfolio = None
    with col1:
        uploaded_file = st.file_uploader("Upload Portfolio File", type="json")
        if uploaded_file:
            portfolio = json.load(uploaded_file)
            st.write("Portfolio Loaded from File:", portfolio)
    with col2:
        if st.button("Load from Cookies"):
            if "portfolio" in cookies:
                portfolio = json.loads(cookies["portfolio"])
                st.write("Portfolio Loaded from Cookies:", portfolio)
            else:
                st.error("No portfolio found in cookies!")
    return portfolio

# Generate QR Code
def save_as_qr(portfolio_data):
    st.write("### Save as QR Code")
    if st.button("Generate QR Code"):
        qr = qrcode.make(json.dumps(portfolio_data))
        st.image(qr, caption="Scan to Load Portfolio")

# Load from QR Code
def load_from_qr():
    st.write("### Load from QR Code")
    uploaded_qr = st.file_uploader("Upload QR Code (PNG/JPG)", type=["png", "jpg"])
    if uploaded_qr:
        qr_image = Image.open(uploaded_qr)
        # Simulated decoding
        decoded_data = '{"token": "BTC", "quantity": 2, "value": 60000}'
        st.write("Decoded Portfolio:", json.loads(decoded_data))

# Main App
def main():
    st.title("🚀 Enhanced Crypto Portfolio Manager 🚀")
    conn, c = init_db()

    # Portfolio Section
    st.subheader("Portfolio")
    display_portfolio(c)

    # Save/Load Portfolio Options
    portfolio_data = [{"token": "BTC", "quantity": 2, "value": 60000}]
    save_portfolio(portfolio_data)
    portfolio = load_portfolio()

    # QR Code Options
    save_as_qr(portfolio_data)
    load_from_qr()

    # Watchlist Section
    st.subheader("Watchlist")
    manage_watchlist(c, conn)

if __name__ == "__main__":
    main()
