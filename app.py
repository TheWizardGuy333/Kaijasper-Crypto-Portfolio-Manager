import os
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager
import json
from PIL import Image
import qrcode
import io  # Import io module for working with byte streams

# Load environment variables
load_dotenv()

CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY")
COOKIES_PASSWORD = os.getenv("COOKIES_PASSWORD")  # Load the cookies password

# Ensure password is loaded
if not COOKIES_PASSWORD:
    st.error("COOKIES_PASSWORD is not set in the environment variables!")
    st.stop()

# Initialize cookies
cookies = EncryptedCookieManager(prefix="crypto_app", password=COOKIES_PASSWORD)  # Pass the password
if not cookies.ready():
    st.stop()

# Default Tokens (you can add more tokens here initially)
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Litecoin": "litecoin",
    "Ripple": "ripple",
    "Solana": "solana",
    "Polkadot": "polkadot"
}

# Function to fetch live data from CryptoCompare API
def fetch_live_data(token):
    url = f"https://min-api.cryptocompare.com/data/price?fsym={token.upper()}&tsyms=USD"
    headers = {
        "Authorization": f"Apikey {CRYPTOCOMPARE_API_KEY}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

# Function to fetch historical data for a token
def fetch_historical_prices(token):
    url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={token.upper()}&tsym=USD&limit=2000"
    headers = {
        "Authorization": f"Apikey {CRYPTOCOMPARE_API_KEY}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()["Data"]["Data"]
        return [(entry['time'], token, entry['close'], entry['time']) for entry in data]
    return None

# Function to generate a QR code
def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    return img

# Function to fetch token details (price, market cap, etc.)
def fetch_token_details(token):
    url = f"https://min-api.cryptocompare.com/data/all/coinlist"
    headers = {
        "Authorization": f"Apikey {CRYPTOCOMPARE_API_KEY}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        tokens = response.json()["Data"]
        token_details = tokens.get(token.upper())
        return token_details if token_details else f"Details for {token} not found"
    return None

# Function to manage token list (Add custom tokens)
def add_custom_token(token_name, token_symbol):
    TOKENS[token_name] = token_symbol

# Main Function to run the Streamlit app
def main():
    # Render the landing page
    st.title("Crypto Portfolio Tracker")
    st.write("Track your cryptocurrency portfolio using live data from various sources.")
    
    # Check if cookies are ready (for any user-specific data)
    if cookies.ready():
        st.write("Cookies are ready!")
    else:
        st.error("Cookies are not ready. Please check the cookie configuration.")
    
    # Sidebar Navigation
    st.sidebar.title("Sidebar Navigation")
    st.sidebar.write("Use the sidebar to explore different features!")

    # Add a feature to add custom tokens
    st.sidebar.subheader("Add Custom Token")
    custom_token_name = st.sidebar.text_input("Token Name (e.g., Bitcoin)")
    custom_token_symbol = st.sidebar.text_input("Token Symbol (e.g., BTC)")

    if st.sidebar.button("Add Custom Token"):
        if custom_token_name and custom_token_symbol:
            add_custom_token(custom_token_name, custom_token_symbol)
            st.sidebar.success(f"Token {custom_token_name} added successfully!")
        else:
            st.sidebar.error("Please fill in both fields to add a custom token.")

    # Allow the user to select a token to display its data
    token_choice = st.selectbox("Select a Token to View", list(TOKENS.keys()))

    # Fetch and display live data for selected token
    st.subheader(f"Live Data for {token_choice}")
    token_symbol = TOKENS[token_choice]
    token_data = fetch_live_data(token_symbol)
    if token_data:
        st.write(f"{token_choice} Price (USD): ${token_data['USD']}")
    else:
        st.error(f"Failed to fetch live data for {token_choice}!")

    # Show the portfolio of tokens (You can update with your portfolio data)
    st.subheader("Your Portfolio")
    portfolio = {
        "Bitcoin": 0.5,
        "Ethereum": 1.2,
        "Dogecoin": 5000
    }
    
    portfolio_df = pd.DataFrame(portfolio.items(), columns=["Token", "Amount"])
    st.write(portfolio_df)

    # Show historical prices of the selected token
    st.subheader("Crypto Price History")
    if st.button('Show Historical Data'):
        historical_prices = fetch_historical_prices(token_symbol)
        if historical_prices:
            df = pd.DataFrame(historical_prices, columns=["ID", "Token", "Price", "Timestamp"])
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit='s')
            fig = px.line(df, x="Timestamp", y="Price", title=f"{token_choice} Price Over Time")
            st.plotly_chart(fig)

    # Show portfolio distribution as a pie chart
    if st.button('Show Portfolio Chart'):
        fig = px.pie(portfolio_df, names='Token', values='Amount', title='Portfolio Distribution')
        st.plotly_chart(fig)

    # Show QR Code generation feature
    if st.button('Generate QR Code'):
        img = generate_qr_code("https://www.cryptotracker.com")
        st.image(img, caption="Your Portfolio QR Code")

    # Show token details if available
    if st.button("Show Token Details"):
        token_info = fetch_token_details(token_symbol)
        if token_info:
            st.write(token_info)
        else:
            st.error("Failed to fetch token details.")
    
    # Displaying a QR Code for any URL (demo)
    if st.button("Generate QR for URL"):
        url = "https://www.cryptotracker.com"
        qr_code = generate_qr_code(url)
        st.image(qr_code, caption="QR Code for CryptoTracker URL")
    
    # Final footer message
    st.markdown("""
    <footer>
        <p>Powered by CryptoCompare API and Streamlit | Developed with ❤️</p>
    </footer>
    """, unsafe_allow_html=True)

# Run the app
if __name__ == "__main__":
    main()
