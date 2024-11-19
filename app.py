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
    exit()

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

# Yahoo Finance token name mapping
def get_yahoo_finance_token_name(token_id):
    token_name_mapping = {
        "bitcoin": "BTC",
        "dogecoin": "DOGE",
    }
    return token_name_mapping.get(token_id, token_id)

# Yahoo Finance price fetcher
def fetch_price_yahoo_finance(token_name):
    try:
        base_url = "https://finance.yahoo.com/quote/"
        search_url = f"{base_url}{token_name}-USD"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
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

# Fetch price from CryptoCompare
def fetch_price_cryptocompare(token_id):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={token_id.upper()}&tsyms=USD"
        headers = {"authorization": f"Apikey {CRYPTOCOMPARE_API_KEY}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return {"price": response.json().get("USD")}
    except requests.RequestException as e:
        logging.error(f"Error fetching price from CryptoCompare for {token_id}: {e}")
        return None

# Fetch price from LiveCoinWatch
def fetch_price_livecoinwatch(token_id):
    try:
        url = "https://api.livecoinwatch.com/coins/single"
        headers = {"x-api-key": LIVECOINWATCH_API_KEY}
        payload = {"code": token_id.upper(), "currency": "USD", "meta": True}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return {"price": response.json().get("rate")}
    except requests.RequestException as e:
        logging.error(f"Error fetching price from LiveCoinWatch for {token_id}: {e}")
        return None

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

# Main app layout
def main():
    st.title("🚀Kaijasper Crypto Portfolio Manager🚀")
    conn, c = init_db()

    menu = ["Home", "Manage Portfolio", "View Portfolio"]
    choice = st.sidebar.selectbox("Select an option", menu)

    if choice == "Home":
        st.subheader("Welcome!")
        st.write("Manage your crypto portfolio with real-time updates.")
        st.subheader("Visit These Websites")
# Buttons for cryptocurrency-related websites
        if st.button("Coinbase"):
            st.write("Redirecting to Coinbase...")
            st.markdown("[Visit Coinbase](https://www.coinbase.com)", unsafe_allow_html=True)
        if st.button("LiveCoinWatch"):
            st.write("Redirecting to LiveCoinWatch...")
            st.markdown("[Visit LiveCoinWatch](https://www.livecoinwatch.com)", unsafe_allow_html=True)
        if st.button("CoinMarketCap"):
            st.write("Redirecting to CoinMarketCap...")
            st.markdown("[Visit CoinMarketCap](https://coinmarketcap.com)", unsafe_allow_html=True)
        if st.button("CoinGecko"):
            st.write("Redirecting to CoinGecko...")
            st.markdown("[Visit CoinGecko](https://www.coingecko.com)", unsafe_allow_html=True)
        if st.button("CryptoCompare"):
            st.write("Redirecting to CryptoCompare...")
            st.markdown("[Visit CryptoCompare](https://www.cryptocompare.com)", unsafe_allow_html=True)
        if st.button("Yahoo Finance"):
            st.write("Redirecting to Yahoo Finance...")
            st.markdown("[Visit Yahoo Finance](https://finance.yahoo.com)", unsafe_allow_html=True)

    elif choice == "Manage Portfolio":
        st.subheader("Manage Your Portfolio")
        token_name = st.selectbox("Select Token to Add", options=list(TOKENS.keys()))
        quantity = st.number_input("Enter Quantity to Add", min_value=0.0, format="%.4f")
        if st.button("Add to Portfolio"):
            token_id = TOKENS.get(token_name)
            if not token_id:
                st.error(f"Token {token_name} not supported.")
                return
            price_info = fetch_price(token_id)
            if price_info and "price" in price_info:
                price = price_info["price"]
                add_token(c, conn, token_name, quantity, price)
                st.success(f"Added {quantity} {token_name} at ${price:.2f}")
                display_portfolio(c)
            else:
                st.error(f"Could not fetch price for {token_name}")

    elif choice == "View Portfolio":
        display_portfolio(c)

    # Close database connection
    conn.close()

            if __name__ == "__main__":
main()
