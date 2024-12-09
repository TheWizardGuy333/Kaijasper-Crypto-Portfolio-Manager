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

# Token List
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
    "Polygon": "polygon",
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
    # Added tokens available on Coinbase
    "Polygon (MATIC)": "matic-network",
    "Immutable X (IMX)": "immutable-x",
    "Arbitrum (ARB)": "arbitrum",
    "Optimism (OP)": "optimism",
    "Fetch.ai (FET)": "fetch-ai",
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
        "polygon": "MATIC",
        "arbitrum": "ARB",
        "optimism": "OP",
        "fetch-ai": "FET",
        "hedera-hashgraph": "HBAR",
        "quant-network": "QNT",
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
    """)  # Changed price and total_value to NUMERIC for better precision
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
        logging.warning(f"Failed to fetch price from LiveCoinWatch for {token_id}, trying Yahoo Finance.")
        yahoo_token_name = get_yahoo_finance_token_name(token_id)
        price = fetch_price_yahoo_finance(yahoo_token_name)
    if price is None:
        logging.error(f"Failed to fetch price for {token_id} from all sources.")
    return price

# Ensure quantity is greater than 0
def validate_quantity(quantity):
    if quantity <= 0:
        st.warning("Quantity must be greater than 0.")
        return False
    return True

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
            price = float(price_tag.text.replace(",", ""))
            return {"price": price}
        logging.warning(f"Could not find price tag on Yahoo Finance page for {token_name}.")
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
            if validate_quantity(quantity):
                token_id = TOKENS.get(token_name)
                price_info = fetch_price(token_id)
                if price_info and "price" in price_info:
                    price = price_info["price"]
                    add_token(c, conn, token_name, quantity, price)
                    st.success(f"Added {quantity} {token_name} at ${price:.2f}")
                    display_portfolio(c)
                else:
                    st.error(f"Could not fetch price for {token_name}")

if __name__ == "__main__":
    main()