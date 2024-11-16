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

# Token List (Your Tokens Included)
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
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
    
    # Provide the option for the user to interact with the app
    st.sidebar.title("Sidebar Navigation")
    st.sidebar.write("Use the sidebar to explore different features!")

    # Add a feature to display live data from APIs (CryptoCompare and LiveCoinWatch)
    if st.button('Show live data'):
        token_data = fetch_live_data("dogecoin")
        if token_data:
            st.write(token_data)
        else:
            st.error("Failed to fetch live data!")

    # Example of displaying the portfolio (you can expand this with real data)
    st.subheader("Your Portfolio")
    portfolio = {
        "Bitcoin": 0.5,
        "Ethereum": 1.2,
        "Dogecoin": 5000
    }
    
    portfolio_df = pd.DataFrame(portfolio.items(), columns=["Token", "Amount"])
    st.write(portfolio_df)

    # Add functionality to display historical prices or a chart
    st.subheader("Crypto Price History")
    if st.button('Show Historical Data'):
        historical_prices = fetch_historical_prices("dogecoin")
        if historical_prices:
            df = pd.DataFrame(historical_prices, columns=["ID", "Token", "Price", "Timestamp"])
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit='s')
            fig = px.line(df, x="Timestamp", y="Price", title="Dogecoin Price Over Time")
            st.plotly_chart(fig)

    # Option to show portfolio chart
    if st.button('Show Portfolio Chart'):
        fig = px.pie(portfolio_df, names='Token', values='Amount', title='Portfolio Distribution')
        st.plotly_chart(fig)

    # Show an image or QR Code
    if st.button('Generate QR Code'):
        img = generate_qr_code("https://www.cryptotracker.com")
        st.image(img, caption="Your Portfolio QR Code")

    # If there is an error in any function, it will stop execution and display an error message.
    if not CRYPTOCOMPARE_API_KEY or not LIVECOINWATCH_API_KEY:
        st.error("API Keys not configured. Please check your environment variables.")
        st.stop()
    
    # Example of fetching token details and displaying them in the app
    if st.button("Show Token Details"):
        token_info = fetch_token_details("dogecoin")
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
