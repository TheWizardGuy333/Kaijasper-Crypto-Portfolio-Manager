import os
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager

# Load environment variables and Streamlit secrets
load_dotenv()
CRYPTOCOMPARE_API_KEY = st.secrets.get("CRYPTOCOMPARE_API_KEY") or os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = st.secrets.get("LIVECOINWATCH_API_KEY") or os.getenv("LIVECOINWATCH_API_KEY")

# Notify if API keys are missing
if not CRYPTOCOMPARE_API_KEY:
    st.warning("Missing CryptoCompare API Key. Some functionalities may not work.")
if not LIVECOINWATCH_API_KEY:
    st.warning("Missing LiveCoinWatch API Key. Some functionalities may not work.")

# Initialize encrypted cookie manager
cookies = EncryptedCookieManager(prefix="crypto_app_")
if not cookies.ready():
    st.stop()

# Password-protected access
def authenticate_user():
    password = cookies.get("user_password")
    if not password:
        st.warning("Please set up a password for access.")
        input_password = st.text_input("Enter a new password", type="password")
        confirm_password = st.text_input("Confirm your password", type="password")
        if st.button("Save Password"):
            if input_password == confirm_password:
                cookies["user_password"] = input_password
                st.success("Password set successfully. Refresh the page to continue.")
                st.experimental_rerun()
            else:
                st.error("Passwords do not match.")
    else:
        input_password = st.text_input("Enter your password", type="password")
        if st.button("Login"):
            if input_password == password:
                st.success("Authentication successful!")
            else:
                st.error("Incorrect password. Please try again.")
                st.stop()

authenticate_user()

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
    "Bonfida": "bonfida"
    # Add your token list as in the original code...
}

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("portfolio.db")
    c = conn.cursor()
    try:
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
    except sqlite3.Error as e:
        st.error(f"Database Error: {e}")
    return conn, c

# Fetch price functions...
# (Use the functions from the original code)

# Main application logic
def main():
    st.title("🚀 Enhanced Crypto Portfolio Manager 🚀")
    conn, c = init_db()
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
