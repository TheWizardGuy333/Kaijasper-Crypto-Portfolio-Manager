import os
import sys
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

# Try importing plotly and handle missing module
try:
    import plotly.express as px
except ModuleNotFoundError:
    st.error("The `plotly` library is not installed. Please install it by running `pip install plotly`.")
    sys.exit("Error: Missing required library `plotly`")

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
    logger.warning("Missing API keys: CryptoCompare or LiveCoinWatch.")

# Token List (Ensure compatibility with all APIs)
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    "Baby Doge": "baby-doge-coin",
    "Kishu Inu": "kishu-inu",
    "Saitama": "saitama",
    "SafeMoon": "safemoon",
    "Akita Inu": "akita-inu",
    "Volt Inu": "volt-inu",
    "CateCoin": "catecoin",
    "Shiba Predator": "shiba-predator",
    "DogeBonk": "dogebonk",
    "Flokinomics": "flokinomics",
    "StarLink": "starlink",
    "DogeGF": "dogegf",
    "Shibaverse": "shibaverse",
    "FEG Token": "feg-token",
    "Dogelon Mars": "dogelon-mars",
    "BabyFloki": "babyfloki",
    "PolyDoge": "polydoge",
    "Moonriver": "moonriver",
    "MetaHero": "metahero",
    "BabyDogeZilla": "babydogezilla",
    "BabyShark": "babyshark",
    "Wakanda Inu": "wakanda-inu",
    "King Shiba": "king-shiba",
    "PepeCoin": "pepecoin",
    "Pitbull": "pitbull",
    "MiniDoge": "minidoge",
    "Bonfida": "bonfida",
}

# Mutex for thread-safe database operations
db_lock = threading.Lock()

# Enable SQLite WAL mode
def enable_wal_mode():
    conn = sqlite3.connect("portfolio.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()

# Get SQLite connection
def get_connection():
    db_path = os.path.join(os.getcwd(), "portfolio.db")
    return sqlite3.connect(db_path, check_same_thread=False)

# Initialize SQLite database
@st.cache_resource
def init_db():
    try:
        enable_wal_mode()
        conn = get_connection()
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
        conn.close()
    except sqlite3.Error as e:
        st.error(f"Database Initialization Error: {e}")
        logger.error(f"Database Initialization Error: {e}")

# Caching for API responses
cache = TTLCache(maxsize=100, ttl=300)  # Cache up to 100 items for 5 minutes

# Fetch price with fallback mechanisms and detailed logging
def fetch_price(token_id):
    try:
        if token_id in cache:
            logger.info(f"Cache hit for token: {token_id}")
            return cache[token_id]
        
        logger.info(f"Fetching price for token: {token_id}")
        
        # Attempt to fetch price from multiple sources and log which source failed
        price = None
        
        # Try Coingecko
        price = fetch_price_coingecko(token_id)
        if not price:
            logger.warning(f"Failed to fetch price for {token_id} from Coingecko.")
        
        # Try CryptoCompare if Coingecko fails
        if not price:
            price = fetch_price_cryptocompare(token_id)
            if not price:
                logger.warning(f"Failed to fetch price for {token_id} from CryptoCompare.")
        
        # Try LiveCoinWatch if both previous APIs fail
        if not price:
            price = fetch_price_livecoinwatch(token_id)
            if not price:
                logger.warning(f"Failed to fetch price for {token_id} from LiveCoinWatch.")
        
        if price:
            cache[token_id] = price
            logger.info(f"Price fetched successfully for {token_id}: {price}")
        else:
            logger.warning(f"Price not found for token: {token_id}")
        return price
    except Exception as e:
        logger.error(f"Error fetching price for {token_id}: {e}")
        return None

# Fetch price from Coingecko
def fetch_price_coingecko(token_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        price = response.json().get(token_id, {}).get("usd")
        logger.info(f"Coingecko price for {token_id}: {price}")
        return {"price": price} if price else None
    except requests.RequestException as e:
        logger.error(f"Coingecko API Error for {token_id}: {e}")
        return None

# Fetch price from CryptoCompare
def fetch_price_cryptocompare(token_id):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={token_id.upper()}&tsyms=USD"
        headers = {"authorization": f"Apikey {CRYPTOCOMPARE_API_KEY}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        price = response.json().get("USD")
        logger.info(f"CryptoCompare price for {token_id}: {price}")
        return {"price": price} if price else None
    except requests.RequestException as e:
        logger.error(f"CryptoCompare API Error for {token_id}: {e}")
        return None

# Fetch price from LiveCoinWatch
def fetch_price_livecoinwatch(token_id):
    try:
        url = "https://api.livecoinwatch.com/coins/single"
        headers = {"x-api-key": LIVECOINWATCH_API_KEY}
        payload = {"code": token_id.upper(), "currency": "USD", "meta": True}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        price = response.json().get("rate")
        logger.info(f"LiveCoinWatch price for {token_id}: {price}")
        return {"price": price} if price else None
    except requests.RequestException as e:
        logger.error(f"LiveCoinWatch API Error for {token_id}: {e}")
        return None

# Add token to portfolio
def add_token(token, quantity, price):
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
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
            st.success(f"Added {quantity} of {token} to portfolio at ${price:.6f} each.")
        except sqlite3.Error as e:
            st.error(f"Database Error: {e}")
            logger.error(f"Database Error: {e}")
        finally:
            conn.close()

# Delete token from portfolio
def delete_token(token):
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute("DELETE FROM portfolio WHERE token = ?", (token,))
            conn.commit()
            st.success(f"{token} has been removed from your portfolio.")
        except sqlite3.Error as e:
            st.error(f"Database Error: {e}")
            logger.error(f"Database Error: {e}")
        finally:
            conn.close()

# Display portfolio
def display_portfolio():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM portfolio", conn)
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
    except sqlite3.Error as e:
        st.error(f"Error displaying portfolio: {e}")
        logger.error(f"Error displaying portfolio: {e}")
    finally:
        conn.close()

# Main app
def main():
    st.title("🚀 Kaijasper Crypto Portfolio Manager 🚀")
    init_db()

    # Portfolio Management
    st.subheader("Portfolio Management")
    display_portfolio()

    # Add Token
    st.subheader("Add a Token to Portfolio")
    token_name = st.selectbox("Select Token", options=list(TOKENS.keys()), key="add_token_portfolio")
    quantity = st.number_input("Enter Quantity", min_value=0.0, step=0.01, key="token_quantity")
    if st.button("Add Token"):
        price = fetch_price(TOKENS[token_name])
        if price:
            add_token(token_name, quantity, price["price"])
        else:
            st.error(f"Could not fetch the price for {token_name}.")
            
    # Delete Token
    st.subheader("Delete a Token from Portfolio")
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        token_list = [row[0] for row in c.execute("SELECT token FROM portfolio")]
        conn.close()
    delete_token_name = st.selectbox("Select Token to Delete", options=token_list, key="delete_token")
    if st.button("Delete Token"):
        delete_token(delete_token_name)

if __name__ == "__main__":
    main()
