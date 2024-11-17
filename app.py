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
import threading

# Load environment variables
load_dotenv()

# API Keys from .env
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY")

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Mutex for thread-safe database access
db_lock = threading.Lock()

# Token list
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    "Baby Doge": "baby-doge-coin",
    "Kishu Inu": "kishu-inu",
    # Add other tokens as needed
}

# Cache for API responses
cache = TTLCache(maxsize=100, ttl=300)  # Cache up to 100 items for 5 minutes

# Database helper functions
def enable_wal_mode():
    """Enable Write-Ahead Logging for better concurrency."""
    with db_lock:
        conn = sqlite3.connect("portfolio.db", check_same_thread=False)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except sqlite3.Error as e:
            logger.error(f"Error enabling WAL mode: {e}")
            st.error("Failed to enable WAL mode for the database.")
        finally:
            conn.close()

def get_connection():
    """Get a new SQLite connection."""
    try:
        return sqlite3.connect("portfolio.db", check_same_thread=False)
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        st.error("Failed to connect to the database.")
        return None

def init_db():
    """Initialize database tables."""
    with db_lock:
        conn = get_connection()
        if not conn:
            return  # Exit early if connection failed
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
        finally:
            conn.close()

# Fetch prices
def fetch_price(token_id):
    """Fetch the price of a token using multiple APIs."""
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
    return None

def fetch_price_coingecko(token_id):
    """Fetch price from CoinGecko."""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        price = response.json().get(token_id, {}).get("usd")
        return {"price": price} if price else None
    except requests.RequestException as e:
        logger.error(f"CoinGecko API Error for {token_id}: {e}")
        return None

# Portfolio operations
def add_token(token, quantity, price):
    """Add a token to the portfolio."""
    with db_lock:
        conn = get_connection()
        if not conn:
            return
        try:
            c = conn.cursor()
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
            st.success(f"Added {quantity} of {token} to portfolio at ${price:.6f} each.")
        except sqlite3.Error as e:
            st.error(f"Database Error: {e}")
            logger.error(f"Database Error: {e}")
        finally:
            conn.close()

def delete_token(token):
    """Delete a token from the portfolio."""
    with db_lock:
        conn = get_connection()
        if not conn:
            return
        try:
            c = conn.cursor()
            c.execute("DELETE FROM portfolio WHERE token = ?", (token,))
            conn.commit()
            st.success(f"{token} has been removed from your portfolio.")
        except sqlite3.Error as e:
            st.error(f"Database Error: {e}")
            logger.error(f"Database Error: {e}")
        finally:
            conn.close()

def display_portfolio():
    """Display the current portfolio."""
    with db_lock:
        conn = get_connection()
        if not conn:
            return
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
        finally:
            conn.close()

# Main application
def main():
    st.title("🚀 Kaijasper Crypto Portfolio Manager 🚀")

    try:
        init_db()
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        st.error("Failed to initialize the database.")

    st.subheader("Portfolio Management")
    display_portfolio()

    st.subheader("Add a Token to Portfolio")
    token_name = st.selectbox("Select Token", options=list(TOKENS.keys()), key="add_token_portfolio")
    quantity = st.number_input("Enter Quantity", min_value=0.0, step=0.01, key="token_quantity")
    if st.button("Add Token"):
        price = fetch_price(TOKENS[token_name])
        if price:
            add_token(token_name, quantity, price["price"])
        else:
            st.error(f"Could not fetch the price for {token_name}.")
            
    st.subheader("Delete a Token from Portfolio")
    with db_lock:
        conn = get_connection()
        token_list = []
        if conn:
            try:
                c = conn.cursor()
                token_list = [row[0] for row in c.execute("SELECT token FROM portfolio")]
            finally:
                conn.close()
    delete_token_name = st.selectbox("Select Token to Delete", options=token_list, key="delete_token")
    if st.button("Delete Token"):
        delete_token(delete_token_name)

if __name__ == "__main__":
    main()
