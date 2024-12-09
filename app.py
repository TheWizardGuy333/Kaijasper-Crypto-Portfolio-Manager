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
    st.stop()  # Halt execution instead of exiting the Streamlit app

# Token List with CoinGecko IDs
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    "Floki Inu": "floki-inu",
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "Cardano": "cardano",
    "Ripple": "ripple",
    "Polkadot": "polkadot",
    "Binance Coin": "binancecoin",
    "Avalanche": "avalanche",
    "Litecoin": "litecoin",
    "Polygon (MATIC)": "matic-network",
    "Amp": "amp",
    "Holo": "holo",
    "Celer Network": "celer-network",
    "JasmyCoin": "jasmycoin",
    "Ankr": "ankr",
    "Fetch.ai": "fetch-ai",
    "IoTeX": "iotex",
    "Request": "request",
    "ConstitutionDAO": "constitutiondao",
    "Origin Protocol": "origin-protocol",
    "Civic": "civic",
    "Verasity": "verasity",
    "StormX": "stormx",
    "Saitama Inu": "saitama",
    "SafeMoon Inu": "safemoon",
    "Kishu Inu": "kishu-inu",
    "Akita Inu": "akita-inu",
    "Pitbull": "pitbull",
    "Baby Doge Coin": "baby-doge-coin",
    "Hoge Finance": "hoge-finance",
    "EverGrow Coin": "evergrow-coin",
    "Bonfire": "bonfire",
    "ElonDoge Token": "elondoge-token",
    "ShibaPup": "shibapup",
    "CateCoin": "catecoin",
    "BitTorrent": "bittorrent",
    "VeChain": "vechain",
    "Stellar": "stellar",
    "Bonfida": "bonfida",
    "Immutable X (IMX)": "immutable-x",
    "Arbitrum (ARB)": "arbitrum",
    "Optimism (OP)": "optimism",
    "SingularityNET (AGIX)": "singularitynet",
    "Ocean Protocol (OCEAN)": "ocean-protocol",
    "Aave (AAVE)": "aave",
    "Curve Finance (CRV)": "curve-dao-token",
    "Render Token (RNDR)": "render-token",
    "Theta Network (THETA)": "theta-token",
    "Flow (FLOW)": "flow",
    "Basic Attention Token (BAT)": "basic-attention-token",
    "Gala Games (GALA)": "gala",
    "The Sandbox (SAND)": "the-sandbox",
    "Enjin Coin (ENJ)": "enjincoin",
    "Hedera (HBAR)": "hedera-hashgraph",
    "Quant (QNT)": "quant-network",
}

# Yahoo Finance token name mapping
def get_yahoo_finance_token_name(token_id):
    token_name_mapping = {
        "bitcoin": "BTC",
        "dogecoin": "DOGE",
        "shiba-inu": "SHIB",
        "floki-inu": "FLOKI",
        "matic-network": "MATIC",
        "arbitrum": "ARB",
        "optimism": "OP",
        "hedera-hashgraph": "HBAR",
        "quant-network": "QNT",
        "theta-token": "THETA",
        "basic-attention-token": "BAT",
        # Add additional mappings if necessary
    }
    return token_name_mapping.get(token_id, token_id)

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
            price NUMERIC,
            total_value NUMERIC
        )
    """)
    conn.commit()
    return conn, c

# Add token to portfolio
def add_token(c, conn, token, quantity, price):
    total_value = quantity * price
    c.execute("INSERT OR REPLACE INTO portfolio (token, quantity, value) VALUES (?, ?, ?)", (token, quantity, total_value))
    c.execute("""
        INSERT INTO transactions (token, date, type, quantity, price, total_value)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (token, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Buy", quantity, price, total_value))
    conn.commit()

# Display portfolio
def display_portfolio(c):
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
        logging.warning(f"Failed to fetch price from LiveCoinWatch for {token_id}, trying Yahoo Finance.")
        yahoo_token_name = get_yahoo_finance_token_name(token_id)
        price = fetch_price_yahoo_finance(yahoo_token_name)
    if price is None:
        logging.error(f"Failed to fetch price for {token_id} from all sources.")
    return price

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
                price_info = fetch_price(token_id)
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