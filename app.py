import os
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
import logging  # For logging errors and events

# Configure logging
logging.basicConfig(level=logging.INFO, filename="app.log", format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables from .env file
load_dotenv()

# Fetch API keys from environment variables
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Check if all API keys are loaded properly
if not CRYPTOCOMPARE_API_KEY or not LIVECOINWATCH_API_KEY or not COINGECKO_API_KEY:
    st.error("API keys are missing! Check the .env file.")
    logging.error("API keys are missing! Check the .env file.")
    exit()

# Token List (Including Bonfida)
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    # Add other tokens here
    "Bonfida": "bonfida"
}

# Initialize SQLite database
def init_db():
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

# Fetch price with fallback mechanism
def fetch_price(token_id):
    price = fetch_price_coingecko(token_id)
    if price is None:
        logging.warning(f"Failed to fetch price from CoinGecko for {token_id}, trying CryptoCompare.")
        price = fetch_price_cryptocompare(token_id)
    if price is None:
        logging.warning(f"Failed to fetch price from CryptoCompare for {token_id}, trying LiveCoinWatch.")
        price = fetch_price_livecoinwatch(token_id)
    if price is None:
        logging.error(f"Failed to fetch price for {token_id} from all sources.")
    return price

def fetch_price_coingecko(token_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd&include_market_cap=true&include_24hr_change=true&include_24hr_vol=true"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get(token_id, {})
        return {
            "price": data.get("usd"),
            "market_cap": data.get("usd_market_cap"),
            "volume": data.get("usd_24h_vol"),
            "change_24h": data.get("usd_24h_change", 0)
        }
    except requests.RequestException as e:
        logging.error(f"Error fetching price from CoinGecko for {token_id}: {e}")
        return None

# Add token to portfolio with validation
def add_token(c, conn, token, quantity, price):
    if quantity <= 0:
        st.error("Quantity must be greater than 0.")
        logging.warning("Attempted to add token with non-positive quantity.")
        return
    total_value = quantity * price
    c.execute("INSERT OR REPLACE INTO portfolio (token, quantity, value) VALUES (?, ?, ?)",
              (token, quantity, total_value))
    c.execute("""
        INSERT INTO transactions (token, date, type, quantity, price, total_value)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (token, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Buy", quantity, price, total_value))
    conn.commit()
    logging.info(f"Added {quantity} of {token} to portfolio at price ${price:.2f}")

def display_portfolio(c):
    st.subheader("Portfolio Overview")
    c.execute("SELECT token, quantity, value FROM portfolio")
    portfolio_data = c.fetchall()

    if portfolio_data:
        df_portfolio = pd.DataFrame(portfolio_data, columns=["Token", "Quantity", "Value (USD)"])
        st.write(df_portfolio)

        # Plot portfolio value
        fig = px.bar(df_portfolio, x="Token", y="Value (USD)", title="Portfolio Value")
        st.plotly_chart(fig)
    else:
        st.write("Your portfolio is empty.")

# Main app layout
def main():
    st.title("Kaijasper Crypto Portfolio Manager")
    conn, c = init_db()

    # Add "Visit Coinbase" to the dropdown menu
    menu = ["Home", "Manage Portfolio", "View Portfolio", "Manage Watchlist", "Visit Coinbase"]
    choice = st.sidebar.selectbox("Select an option", menu)

    if choice == "Home":
        st.subheader("Welcome to Kaijasper Crypto Portfolio Manager!")
        st.write("This app helps you manage your crypto portfolio and watchlist in real-time.")

    elif choice == "Manage Portfolio":
        token_name = st.selectbox("Select Token to Add", options=list(TOKENS.keys()))
        quantity = st.number_input("Enter Quantity to Add", min_value=0.0, format="%.4f")
        if st.button("Add to Portfolio"):
            token_id = TOKENS[token_name]
            price_info = fetch_price(token_id)
            if price_info and "price" in price_info:
                price = price_info["price"]
                add_token(c, conn, token_name, quantity, price)
                st.success(f"Added {quantity} of {token_name} to your portfolio at ${price:.2f}.")
                display_portfolio(c)
            else:
                st.error(f"Could not fetch price for {token_name}.")

    elif choice == "View Portfolio":
        display_portfolio(c)

    elif choice == "Manage Watchlist":
        # Watchlist management remains the same
        pass

    elif choice == "Visit Coinbase":
        st.subheader("Visit Coinbase")
        st.markdown("[Click here to explore Coinbase](https://www.coinbase.com/explore)", unsafe_allow_html=True)

    conn.close()

if __name__ == "__main__":
    main()
