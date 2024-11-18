import os
import pandas as pd
import requests
import sqlite3
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from cachetools import TTLCache
import logging
import plotly.express as px

# Load environment variables
load_dotenv()

# API Keys from .env
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY")

if not CRYPTOCOMPARE_API_KEY or not LIVECOINWATCH_API_KEY:
    raise ValueError("API keys are missing. Check your .env file!")

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Token list
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    # ... other tokens
}


def connect_to_db():
    """Connect to the SQLite database."""
    try:
        conn = sqlite3.connect("portfolio.db")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        st.error("Failed to connect to the database.")
        return None


def init_db(conn):
    """Initialize database tables if they don't exist."""
    try:
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
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database Initialization Error: {e}")
        st.error("Database Initialization Error.")


# Fetch prices
def fetch_price(token_id):
    """Fetch the price of a token using multiple APIs."""
    cache = TTLCache(maxsize=100, ttl=300)  # Create a new cache instance per call
    try:
        if token_id in cache:
            return cache[token_id]

        # Try CoinGecko
        price = fetch_price_coingecko(token_id)
        if price:
            cache[token_id] = price
            return price
    except Exception as e:
        logger.error(f"Error fetching price for {token_id}: {e}")
        st.error(f"Failed to fetch price for {token_id}. Please try again later.")
    return None

def fetch_price_coingecko(token_id):
    """Fetch price from CoinGecko with basic rate-limiting."""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_
        # ... (rest of the code)

def display_portfolio(conn):
    """Display the current portfolio."""
    try:
        query = "SELECT * FROM portfolio"
        df = pd.read_sql_query(query, conn)
        if df.empty:
            st.write("Your portfolio is empty!")
            return
        total_value = df["value"].sum()
        st.write("### Your Portfolio")
        st.write(df)
        st.write(f"**Total Portfolio Value:** ${total_value:,.2f}")
        if st.checkbox("Show Portfolio Allocation Chart", key="portfolio_chart"):
            fig = px.pie(df, values="value", names="token", title="Portfolio Allocation")
            st.plotly_chart(fig)
    except Exception as e:
        st.error(f"Error displaying portfolio: {e}")
        logger.error(f"Error displaying portfolio: {e}")

# Main application
def main():
    st.title("🚀 Kaijasper Crypto Portfolio Manager 🚀")

    conn = connect_to_db()
    if not conn:
        return

    init_db(conn)

    st.subheader("Portfolio Management")
    display_portfolio(conn)

    # ... (rest of the main function)

    conn.close()  # Close the connection at the end of the app

if __name__ == "__main__":
    main()
