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

        conn.commit()

        return conn, c

    except sqlite3.Error as e:

        st.error(f"Database Initialization Error: {e}")

        logger.error(f"Database Initialization Error: {e}")

        return None, None



# Add the "Visit Coinbase" button

def add_coinbase_button():

    st.button("Visit Coinbase", on_click=lambda: st.sidebar.markdown(f"[Visit Coinbase](https://www.coinbase.com/explore/s/listed)", unsafe_allow_html=True))



# Caching for API responses

cache = TTLCache(maxsize=100, ttl=300)  # Cache up to 100 items for 5 minutes



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

def add_token(c, conn, token, quantity, price):

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



# Delete token from portfolio

def delete_token(c, conn, token):

    try:

        c.execute("DELETE FROM portfolio WHERE token = ?", (token,))

        conn.commit()

        st.success(f"{token} has been removed from your portfolio.")

    except sqlite3.Error as e:

        st.error(f"Database Error: {e}")

        logger.error(f"Database Error: {e}")



# Display portfolio data

def display_portfolio():

    conn, c = init_db()

    c.execute("SELECT token, quantity, value FROM portfolio")

    rows = c.fetchall()

    if rows:

        df = pd.DataFrame(rows, columns=["Token", "Quantity", "Value"])

        st.dataframe(df)

    else:

        st.write("Your portfolio is empty.")



# Your Streamlit app code continues below...

st.title("🚀 Kaijasper Crypto Portfolio Manager 🚀")



# Add the Coinbase button at the top (Standalone)

add_coinbase_button()



# Portfolio Management Section

st.subheader("Portfolio Management")

display_portfolio()



# Add the Coinbase button in a section (Learn More)

st.subheader("Learn More")

st.write("For additional information on buying and selling cryptocurrency, you can visit:")

add_coinbase_button()



# Continue with the rest of your app...

# Function to add a new token to the portfolio (via Streamlit form)

def add_token_form():

    conn, c = init_db()

    

    with st.form(key='add_token_form'):

        st.subheader("Add Token to Portfolio")

        

        token = st.selectbox("Choose Token", list(TOKENS.keys()))

        quantity = st.number_input(f"Quantity of {token}:", min_value=0.01, step=0.01)

        price = fetch_price(TOKENS[token])  # Get the price from the selected API

        

        if price:

            st.write(f"Current Price: ${price['price']:.6f}")

        else:

            st.warning(f"Could not fetch price for {token}.")

            return

        

        submit_button = st.form_submit_button(label="Add to Portfolio")

        

        if submit_button:

            if quantity > 0:

                add_token(c, conn, token, quantity, price['price'])

            else:

                st.warning("Quantity must be greater than 0.")



# Function to remove a token from the portfolio (via Streamlit button)

def remove_token_button():

    conn, c = init_db()

    

    st.subheader("Remove Token from Portfolio")

    c.execute("SELECT token FROM portfolio")

    tokens_in_portfolio = [row[0] for row in c.fetchall()]

    

    if tokens_in_portfolio:

        token_to_remove = st.selectbox("Choose Token to Remove", tokens_in_portfolio)

        if st.button("Remove Token"):

            delete_token(c, conn, token_to_remove)

    else:

        st.write("Your portfolio is empty. Nothing to remove.")



# Function to visualize the portfolio's token values

def visualize_portfolio():

    conn, c = init_db()

    

    st.subheader("Portfolio Visualization")

    c.execute("SELECT token, value FROM portfolio")

    rows = c.fetchall()

    

    if rows:

        df = pd.DataFrame(rows, columns=["Token", "Value"])

        fig = px.pie(df, names='Token', values='Value', title="Portfolio Token Distribution")

        st.plotly_chart(fig)

    else:

        st.write("Your portfolio is empty.")



# Display Portfolio Overview

def portfolio_overview():

    conn, c = init_db()

    c.execute("SELECT token, quantity, value FROM portfolio")

    rows = c.fetchall()

    

    if rows:

        st.subheader("Current Portfolio Overview")

        df = pd.DataFrame(rows, columns=["Token", "Quantity", "Value"])

        st.dataframe(df)

    else:

        st.write("Your portfolio is empty. Add tokens to start building it!")



# Function to view and manage the watchlist

def manage_watchlist():

    conn, c = init_db()

    

    st.subheader("Manage Watchlist")

    

    # Display current watchlist

    c.execute("SELECT token FROM watchlist")

    watchlist_tokens = [row[0] for row in c.fetchall()]

    

    st.write("Watchlist Tokens:")

    if watchlist_tokens:

        st.write(watchlist_tokens)

    else:

        st.write("Your watchlist is empty.")

    

    # Add token to watchlist

    token_to_add = st.selectbox("Add Token to Watchlist", list(TOKENS.keys()))

    if st.button("Add to Watchlist"):

        try:

            c.execute("INSERT INTO watchlist (token) VALUES (?)", (token_to_add,))

            conn.commit()

            st.success(f"{token_to_add} has been added to your watchlist.")

        except sqlite3.Error as e:

            st.error(f"Error adding token to watchlist: {e}")

    

    # Remove token from watchlist

    if watchlist_tokens:

        token_to_remove = st.selectbox("Remove Token from Watchlist", watchlist_tokens)

        if st.button("Remove from Watchlist"):

            try:

                c.execute("DELETE FROM watchlist WHERE token = ?", (token_to_remove,))

                conn.commit()

                st.success(f"{token_to_remove} has been removed from your watchlist.")

            except sqlite3.Error as e:

                st.error(f"Error removing token from watchlist: {e}")



# Displaying recent transactions

def display_transactions():

    conn, c = init_db()

    

    st.subheader("Transaction History")

    c.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT 10")

    transactions = c.fetchall()

    

    if transactions:

        df = pd.DataFrame(transactions, columns=["ID", "Token", "Date", "Type", "Quantity", "Price", "Total Value"])

        st.dataframe(df)

    else:

        st.write("No transactions found.")



# Main function to run the Streamlit app

def main():

    # Streamlit sidebar navigation

    st.sidebar.title("Navigation")

    option = st.sidebar.radio("Choose an option", 

                              ["Portfolio Overview", 

                               "Add Token", 

                               "Remove Token", 

                               "Visualize Portfolio", 

                               "Manage Watchlist", 

                               "Transaction History"])

    

    # Display based on selected option

    if option == "Portfolio Overview":

        portfolio_overview()

    elif option == "Add Token":

        add_token_form()

    elif option == "Remove Token":

        remove_token_button()

    elif option == "Visualize Portfolio":

        visualize_portfolio()

    elif option == "Manage Watchlist":

        manage_watchlist()

    elif option == "Transaction History":

        display_transactions()



if __name__ == "__main__":

    main()
