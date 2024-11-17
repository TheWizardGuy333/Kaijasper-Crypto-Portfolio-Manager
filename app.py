import os
import sys
import pandas as pd
import requests
import sqlite3
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from cachetools import TTLCache
import time
import logging

# Try importing plotly and handle missing module
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ModuleNotFoundError:
    st.error("The `plotly` library is not installed. Please install it by running `pip install plotly`.")
    sys.exit("Error: Missing required library `plotly`")

# Setup logging
logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables from .env file
if not os.path.exists(".env"):
    st.error("The .env file is missing!")
    sys.exit("Error: Missing .env file.")

load_dotenv()

# Fetching API keys from environment variables
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY")

# Notify if API keys are missing
if not CRYPTOCOMPARE_API_KEY or not LIVECOINWATCH_API_KEY:
    st.error("API keys are missing! Please provide valid keys in your .env file.")
    sys.exit("Error: Missing API keys.")

# Initialize token list (dynamic tokens added via user input)
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    # Add other tokens dynamically via the app...
}

# Initialize SQLite database
@st.cache_resource
def init_db():
    try:
        db_path = os.path.join(os.getcwd(), "portfolio.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
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
        c.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                token TEXT PRIMARY KEY,
                threshold REAL,
                direction TEXT
            )
        """)
        conn.commit()
        return conn, c
    except sqlite3.Error as e:
        st.error(f"Database Initialization Error: {e}")
        logger.error(f"Database Initialization Error: {e}")
        return None, None

# Caching for API responses
cache = TTLCache(maxsize=100, ttl=300)

# Fetch price with fallback mechanisms
def fetch_price(token_id, currency="usd"):
    if token_id in cache:
        return cache[token_id]
    price = fetch_price_coingecko(token_id, currency) or fetch_price_cryptocompare(token_id) or fetch_price_livecoinwatch(token_id)
    if price:
        cache[token_id] = price
    return price

def fetch_price_coingecko(token_id, currency="usd"):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies={currency}"
        response = requests.get(url)
        response.raise_for_status()
        return {"price": response.json().get(token_id, {}).get(currency)}
    except requests.RequestException as e:
        logger.error(f"Coingecko API Error: {e}")
        return None

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

def fetch_price_livecoinwatch(token_id):
    try:
        url = "https://api.livecoinwatch.com/coins/single"
        headers = {"x-api-key": LIVECOINWATCH_API_KEY}
        payload = {"code": token_id.upper(), "currency": "USD", "meta": True}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return {"price": response.json().get("rate")}
    except requests.RequestException as e:
        logger.error(f"LiveCoinWatch API Error: {e}")
        return None

# Add new token dynamically by fetching from CoinGecko
def add_new_token(token_name):
    try:
        token_id = token_name.lower().replace(" ", "-")
        url = f"https://api.coingecko.com/api/v3/coins/{token_id}"
        response = requests.get(url)
        response.raise_for_status()
        TOKENS[token_name] = token_id
        st.success(f"Token '{token_name}' added successfully!")
    except requests.RequestException as e:
        st.error(f"Failed to add token '{token_name}': {e}")
        logger.error(f"Error adding token '{token_name}': {e}")

# Main app
def main():
    st.title("🚀 Crypto Portfolio Manager 🚀")
    conn, c = init_db()
    if conn and c:
        # Check Price Alerts
        st.subheader("🚨 Price Alerts")
        check_price_alerts(c)

        # Portfolio Management
        st.subheader("Portfolio Management")
        display_portfolio(c)

        # Add Token
        st.subheader("Add a Token to Portfolio")
        token_name = st.selectbox("Select Token", options=list(TOKENS.keys()), key="add_token_portfolio")
        quantity = st.number_input("Enter Quantity", min_value=0.0, step=0.01, key="token_quantity")
        if st.button("Add Token", key="add_token"):
            token_id = TOKENS.get(token_name)
            if token_id:
                price_info = fetch_price(token_id)
                if price_info and price_info.get("price"):
                    add_token(c, conn, token_name, quantity, price_info["price"])
                else:
                    st.error("Failed to fetch the token price. Please try again.")
            else:
                st.error("Invalid token selection.")

        # Delete Token
        st.subheader("Delete a Token from Portfolio")
        tokens_in_portfolio = [row[0] for row in c.execute("SELECT token FROM portfolio").fetchall()]
        if tokens_in_portfolio:
            token_to_delete = st.selectbox("Select Token to Delete", options=tokens_in_portfolio, key="delete_token")
            if st.button("Delete Token", key="delete_token_btn"):
                delete_token(c, conn, token_to_delete)
        else:
            st.write("No tokens in portfolio to delete.")

        # Token Performance Tracking
        st.subheader("Token Performance Tracking")
        if st.button("Show Performance", key="performance"):
            calculate_percentage_change(c)

        # Transaction History
        st.subheader("Transaction History")
        if st.button("View Transactions", key="view_transactions"):
            display_transactions(c)

        # Watchlist Management
        st.subheader("Manage Watchlist")
        manage_watchlist(c, conn)

        # Add New Token
        st.subheader("Add a New Token")
        new_token_name = st.text_input("Enter New Token Name (e.g., 'Shiba Inu')", key="new_token")
        if st.button("Add New Token", key="add_new_token"):
            add_new_token(new_token_name)

        # View Historical Prices
        st.subheader("View Historical Prices")
        selected_token = st.selectbox("Select Token for Historical Prices", options=list(TOKENS.keys()), key="historical_token")
        days = st.slider("Select Number of Days", min_value=1, max_value=365, value=30, step=1, key="days_historical")
        if st.button("Show Historical Prices", key="show_historical"):
            token_id = TOKENS.get(selected_token)
            if token_id:
                display_historical_prices(token_id, days=days)
            else:
                st.error("Invalid token selection.")

        # Manage Price Alerts
        manage_price_alerts(c, conn)

        # Database Management
        st.subheader("Database Management")
        if st.button("Backup Database", key="backup_db"):
            backup_database()
        if st.button("Restore Database", key="restore_db"):
            restore_database()

        # Log Viewer
        st.subheader("View Logs")
        if st.checkbox("Show Logs", key="view_logs"):
            view_logs()

if __name__ == "__main__":
    main()
