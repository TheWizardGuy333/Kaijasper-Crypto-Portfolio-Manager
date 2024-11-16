import os
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from cachetools import TTLCache
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY")

# Notify if API keys are missing
if not CRYPTOCOMPARE_API_KEY or not LIVECOINWATCH_API_KEY:
    st.warning("Some API keys are missing. Certain functionalities may not work.")

# Token List (Including Bonfida)
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
    "Bonfida": "bonfida",
    "Rexas Finance": "rexas-finance",
    # Add other tokens as required...
}

# Initialize SQLite database
def init_db():
    try:
        conn = sqlite3.connect("portfolio.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                token TEXT PRIMARY KEY,
                quantity REAL,
                value REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT,
                date TEXT,
                type TEXT,
                quantity REAL,
                price REAL,
                total_value REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                token TEXT PRIMARY KEY
            )
        """)
        conn.commit()
        return conn, c
    except sqlite3.Error as e:
        st.error(f"Database Initialization Error: {e}")
        return None, None

# Caching for API responses
cache = TTLCache(maxsize=100, ttl=300)  # Cache up to 100 items for 5 minutes

# Fetch price with rate limiting and fallback mechanisms
def fetch_price(token_id):
    if token_id in cache:
        return cache[token_id]
    
    price = fetch_price_coingecko(token_id)
    if price is None:
        price = fetch_price_cryptocompare(token_id)
    if price is None:
        price = fetch_price_livecoinwatch(token_id)
    if price:
        cache[token_id] = price
    return price

# Fetch price from Coingecko
def fetch_price_coingecko(token_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd&include_market_cap=true&include_24hr_change=true&include_24hr_vol=true"
        response = requests.get(url)
        if response.status_code == 429:
            logger.warning("Rate limit hit. Retrying after 2 seconds...")
            time.sleep(2)
            response = requests.get(url)
        response.raise_for_status()
        data = response.json().get(token_id, {})
        return {
            "price": data.get("usd"),
            "market_cap": data.get("usd_market_cap"),
            "volume": data.get("usd_24h_vol"),
            "change_24h": data.get("usd_24h_change"),
        }
    except requests.RequestException as e:
        logger.error(f"Coingecko API Error: {e}")
        return None

# Fetch price from CryptoCompare
def fetch_price_cryptocompare(token_id):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={token_id.upper()}&tsyms=USD"
        headers = {"authorization": f"Apikey {CRYPTOCOMPARE_API_KEY}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return {"price": response.json().get("USD")}
    except requests.RequestException as e:
        logger.error(f"CryptoCompare API Error: {e}")
        return None

# Fetch price from LiveCoinWatch
def fetch_price_livecoinwatch(token_id):
    try:
        url = "https://api.livecoinwatch.com/coins/single"
        headers = {"x-api-key": LIVECOINWATCH_API_KEY}
        payload = {"code": token_id.upper(), "currency": "USD", "meta": True}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return {"price": data.get("rate")}
    except requests.RequestException as e:
        logger.error(f"LiveCoinWatch API Error: {e}")
        return None

# Add token to portfolio
def add_token(c, conn, token, quantity, price):
    try:
        c.execute("SELECT quantity FROM portfolio WHERE token = ?", (token,))
        existing = c.fetchone()
        if existing:
            new_quantity = existing[0] + quantity
            new_value = new_quantity * price
            c.execute("UPDATE portfolio SET quantity = ?, value = ? WHERE token = ?", (new_quantity, new_value, token))
        else:
            total_value = quantity * price
            c.execute("INSERT INTO portfolio (token, quantity, value) VALUES (?, ?, ?)", (token, quantity, total_value))
        c.execute("""
            INSERT INTO transactions (token, date, type, quantity, price, total_value)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (token, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Buy", quantity, price, total_value))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database Error: {e}")

# Display portfolio
def display_portfolio(c):
    c.execute("SELECT * FROM portfolio")
    data = c.fetchall()
    if not data:
        st.write("Your portfolio is empty!")
        return
    df = pd.DataFrame(data, columns=["Token", "Quantity", "Value"])
    total_value = df["Value"].sum()
    st.write("### Your Portfolio")
    st.write(df)
    st.write(f"**Total Portfolio Value:** ${total_value:,.2f}")
    if st.checkbox("Show Portfolio Allocation Chart", key="portfolio_chart"):
        fig = px.pie(df, values="Value", names="Token", title="Portfolio Allocation")
        st.plotly_chart(fig)

# Manage and display watchlist with live prices and changes
def manage_watchlist(c, conn):
    st.subheader("Manage Watchlist")
    token_name = st.selectbox("Select Token to Add/Remove", options=list(TOKENS.keys()), key="manage_watchlist")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Add to Watchlist", key="add_watchlist"):
            c.execute("SELECT token FROM watchlist WHERE token = ?", (token_name,))
            if c.fetchone():
                st.warning(f"{token_name} is already in your watchlist.")
            else:
                c.execute("INSERT INTO watchlist (token) VALUES (?)", (token_name,))
                conn.commit()
                st.success(f"{token_name} added to your watchlist.")
    with col2:
        if st.button("Remove from Watchlist", key="remove_watchlist"):
            c.execute("DELETE FROM watchlist WHERE token = ?", (token_name,))
            conn.commit()
            st.success(f"{token_name} removed from your watchlist.")
    st.write("### Your Watchlist")
    c.execute("SELECT token FROM watchlist")
    tokens = c.fetchall()
    if tokens:
        watchlist_data = []
        for token in tokens:
            token_name = token[0]
            token_id = TOKENS.get(token_name)
            if token_id:
                price_info = fetch_price(token_id)
                if price_info:
                    price = price_info.get("price", "N/A")
                    change_24h = price_info.get("change_24h", "N/A")
                    watchlist_data.append({"Token": token_name, "Price (USD)": price, "24h Change (%)": change_24h})
                else:
                    watchlist_data.append({"Token": token_name, "Price (USD)": "N/A", "24h Change (%)": "N/A"})
        df_watchlist = pd.DataFrame(watchlist_data)
        # Safely format data
        df_watchlist["Price (USD)"] = pd.to_numeric(df_watchlist["Price (USD)"], errors="coerce").fillna(0)
        df_watchlist["24h Change (%)"] = pd.to_numeric(df_watchlist["24h Change (%)"], errors="coerce").fillna(0)
        st.write(df_watchlist.style.format({"Price (USD)": "${:.6f}", "24h Change (%)": "{:.2f}%"}))
    else:
        st.write("Your watchlist is empty.")
    if st.button("Clear Watchlist", key="clear_watchlist"):
        c.execute("DELETE FROM watchlist")
        conn.commit()
        st.success("Watchlist cleared.")

# Main app
def main():
    st.title("🚀 Kaijasper Crypto Portfolio Manager 🚀")
    conn, c = init_db()
    if conn and c:
        st.subheader("Portfolio Management")
        display_portfolio(c)
        st.subheader("Manage Watchlist")
        manage_watchlist(c, conn)
        st.subheader("Add a Token to Your Portfolio")
        token_name = st.selectbox("Select Token", options=list(TOKENS.keys()), key="add_token_portfolio")
        quantity = st.number_input("Enter Quantity Owned", min_value=0.0, step=0.01, key="token_quantity")
        if st.button("Add Token", key="add_token"):
            token_id = TOKENS.get(token_name)
            if not token_id:
                st.error("Invalid token selection.")
                return
            price_info = fetch_price(token_id)
            if price_info and price_info.get("price"):
                add_token(c, conn, token_name, quantity, price_info["price"])
                st.success(f"Added {quantity} of {token_name} at ${price_info['price']:.6f} each.")
            else:
                st.error("Failed to fetch the price. Please try again.")

if __name__ == "__main__":
    main()
