import os
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API keys
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Token List with CoinGecko IDs
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    "Polygon (MATIC)": "matic-network",
    # Add more tokens as needed...
}

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("portfolio.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            token TEXT PRIMARY KEY,
            quantity REAL NOT NULL,
            value REAL NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            total_value REAL NOT NULL
        )
    """)
    conn.commit()
    return conn, c

# Add token to portfolio
def add_token(c, conn, token, quantity, price):
    total_value = quantity * price
    try:
        # Update portfolio table
        c.execute("""
            INSERT INTO portfolio (token, quantity, value)
            VALUES (?, ?, ?)
            ON CONFLICT(token) DO UPDATE SET
            quantity = quantity + excluded.quantity,
            value = value + excluded.value
        """, (token, quantity, total_value))
        
        # Add to transactions table
        c.execute("""
            INSERT INTO transactions (token, date, type, quantity, price, total_value)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (token, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Buy", quantity, price, total_value))
        
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")

# Display portfolio
def display_portfolio(c):
    st.subheader("Portfolio Overview")
    try:
        c.execute("SELECT token, quantity, value FROM portfolio")
        portfolio_data = c.fetchall()

        if portfolio_data:
            df_portfolio = pd.DataFrame(portfolio_data, columns=["Token", "Quantity", "Value (USD)"])
            total_value = df_portfolio['Value (USD)'].sum()
            st.write(f"Total Portfolio Value: ${total_value:.2f}")
            st.dataframe(df_portfolio)
            
            # Plot bar chart
            fig_bar = px.bar(df_portfolio, x="Token", y="Value (USD)", title="Portfolio Value")
            st.plotly_chart(fig_bar)
            
            # Plot pie chart
            fig_pie = px.pie(df_portfolio, values="Value (USD)", names="Token", title="Portfolio Composition")
            st.plotly_chart(fig_pie)
        else:
            st.write("Your portfolio is empty.")
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")

# Fetch price from CoinGecko
def fetch_price(token_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get(token_id, {})
        return {"price": data.get("usd")}
    except requests.RequestException as e:
        st.error(f"Network error: {e}")
        return None
    except Exception as e:
        st.error(f"Error fetching price for {token_id}: {e}")
        return None

# Main app layout
def main():
    st.title("Crypto Portfolio Manager")
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
                else:
                    st.error(f"Could not fetch price for {token_name}")
            else:
                st.warning("Quantity must be greater than 0.")

    elif choice == "View Portfolio":
        display_portfolio(c)

if __name__ == "__main__":
    main()