import os
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
import logging  # For logging errors and events
from bs4 import BeautifulSoup  # For web scraping Yahoo Finance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename="app.log",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load environment variables from .env file
load_dotenv()

# Fetch API keys from environment variables
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Check if all API keys are loaded properly
def check_api_keys():
    if not CRYPTOCOMPARE_API_KEY:
        logging.error("CRYPTOCOMPARE_API_KEY is missing!")
    if not LIVECOINWATCH_API_KEY:
        logging.error("LIVECOINWATCH_API_KEY is missing!")
    if not COINGECKO_API_KEY:
        logging.error("COINGECKO_API_KEY is missing!")
    if not (CRYPTOCOMPARE_API_KEY and LIVECOINWATCH_API_KEY and COINGECKO_API_KEY):
        st.error("API keys are missing! Check the .env file.")
        logging.error("One or more API keys are missing! App cannot proceed.")
        st.stop()

check_api_keys()

# Token List with CoinGecko IDs
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    "Polygon (MATIC)": "matic-network",
    # Add more tokens...
}

# Yahoo Finance token name mapping
def get_yahoo_finance_token_name(token_id):
    token_name_mapping = {
        "bitcoin": "BTC",
        "dogecoin": "DOGE",
        "shiba-inu": "SHIB",
        "matic-network": "MATIC",
        # Add other mappings if necessary
    }
    return token_name_mapping.get(token_id, token_id)

# Initialize SQLite database with self-repair
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
                price NUMERIC,
                total_value NUMERIC
            )
        """)
        conn.commit()
        return conn, c
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        st.error("Failed to initialize the database. Please check logs.")
        st.stop()

# Add token to portfolio
def add_token(c, conn, token, quantity, price):
    try:
        total_value = quantity * price
        c.execute("INSERT OR REPLACE INTO portfolio (token, quantity, value) VALUES (?, ?, ?)", (token, quantity, total_value))
        c.execute("""
            INSERT INTO transactions (token, date, type, quantity, price, total_value)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (token, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Buy", quantity, price, total_value))
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error adding token to portfolio: {e}")
        st.error("An error occurred while updating your portfolio. Please try again.")

# Display portfolio
def display_portfolio(c):
    try:
        st.subheader("Portfolio Overview")
        c.execute("SELECT token, quantity, value FROM portfolio")
        portfolio_data = c.fetchall()

        if portfolio_data:
            df_portfolio = pd.DataFrame(portfolio_data, columns=["Token", "Quantity", "Value (USD)"])
            total_value = df_portfolio['Value (USD)'].sum()
            st.write(f"Total Portfolio Value: ${total_value:.2f}")
            st.write(df_portfolio)
            fig_bar = px.bar(df_portfolio, x="Token", y="Value (USD)", title="Portfolio Value")
            st.plotly_chart(fig_bar)
            fig_pie = px.pie(df_portfolio, values='Value (USD)', names='Token', title='Portfolio Composition')
            st.plotly_chart(fig_pie)
        else:
            st.write("Your portfolio is empty.")
    except sqlite3.Error as e:
        logging.error(f"Error displaying portfolio: {e}")
        st.error("Failed to load your portfolio. Please check the logs.")

# Fetch price from CoinGecko
def fetch_price_coingecko(token_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get(token_id, {})
        return {"price": data.get("usd")}
    except requests.RequestException as e:
        logging.error(f"Error fetching price from CoinGecko for {token_id}: {e}")
        return None

# Fetch price from Yahoo Finance
def fetch_price_yahoo_finance(token_name):
    try:
        base_url = "https://finance.yahoo.com/quote/"
        search_url = f"{base_url}{token_name}-USD"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        price_tag = soup.find("fin-streamer", {"data-field": "regularMarketPrice"})

        if price_tag:
            return {"price": float(price_tag.text.replace(",", ""))}
        logging.warning(f"Price tag not found on Yahoo Finance for {token_name}.")
        return None
    except Exception as e:
        logging.error(f"Error fetching price from Yahoo Finance for {token_name}: {e}")
        return None

# Main app layout
def main():
    st.title("🚀Kaijasper Crypto Portfolio Manager🚀")
    conn, c = init_db()

    menu = ["Home", "Manage Portfolio", "View Portfolio"]
    choice = st.sidebar.selectbox("Select an option", menu)

    if choice == "Manage Portfolio":
        st.subheader("Manage Your Portfolio")
        token_name = st.selectbox("Select Token to Add", options=list(TOKENS.keys()))
        quantity = st.number_input("Enter Quantity to Add", min_value=0.0, format="%.4f")
        if st.button("Add to Portfolio"):
            if quantity > 0:
                token_id = TOKENS.get(token_name)
                price_info = fetch_price_coingecko(token_id)
                if not price_info:  # Fallback to Yahoo Finance
                    yahoo_token = get_yahoo_finance_token_name(token_id)
                    price_info = fetch_price_yahoo_finance(yahoo_token)
                if price_info and "price" in price_info:
                    price = price_info["price"]
                    add_token(c, conn, token_name, quantity, price)
                    st.success(f"Added {quantity} {token_name} at ${price:.2f}")
                    display_portfolio(c)
                else:
                    st.error(f"Could not fetch price for {token_name}")
            else:
                st.warning("Quantity must be greater than 0.")

    elif choice == "View Portfolio":
        display_portfolio(c)

if __name__ == "__main__":
    main()