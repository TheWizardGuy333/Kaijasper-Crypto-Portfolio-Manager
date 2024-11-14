import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Token List
TOKENS = {
    "BONK": "bonk",
    "Dogecoin": "dogecoin",
    "Shiba Inu": "shiba-inu",
    "Floki Inu": "floki-inu",
    "Baby Doge": "baby-doge-coin",
    "Kishu Inu": "kishu-inu",
    "Saitama": "saitama",
    "Aleo": "aleo",  # Placeholder, Aleo not listed on CoinGecko; customize as needed.
    "Bonfida": "bonfida",
    "Cult DAO": "cult-dao",
    "Hoge Finance": "hoge-finance",
}

# Fetch price data from CoinGecko
def fetch_price(token_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()[token_id]['usd']
    except Exception as e:
        st.error(f"Error fetching price for {token_id}: {e}")
        return None

# Update portfolio with current prices and calculate values
def update_portfolio(portfolio):
    for index, row in portfolio.iterrows():
        token_id = TOKENS.get(row['Token'])
        if token_id:
            price = fetch_price(token_id)
            if price:
                portfolio.at[index, 'Current Price'] = price
                portfolio.at[index, 'Value'] = price * row['Quantity']
    return portfolio

# Streamlit UI
st.title("AI-Driven Crypto Portfolio Manager")

# Session state for portfolio
if 'portfolio' not in st.session_state:
    st.session_state['portfolio'] = pd.DataFrame(columns=['Token', 'Quantity', 'Current Price', 'Value'])

# Add token input
st.subheader("Add a Token to Your Portfolio")
token = st.selectbox("Select Token", options=TOKENS.keys())
quantity = st.number_input("Enter Quantity Owned", min_value=0.0, step=0.01)

if st.button("Add to Portfolio"):
    if token in st.session_state['portfolio']['Token'].values:
        st.warning("Token already exists in portfolio. Update the quantity instead.")
    else:
        # Create a new row as a DataFrame
        new_row = pd.DataFrame([{'Token': token, 'Quantity': quantity, 'Current Price': 0, 'Value': 0}])
        # Concatenate the new row with the existing portfolio
        st.session_state['portfolio'] = pd.concat([st.session_state['portfolio'], new_row], ignore_index=True)

# Display and update portfolio
st.subheader("Your Portfolio")
if not st.session_state['portfolio'].empty:
    st.session_state['portfolio'] = update_portfolio(st.session_state['portfolio'])
    st.write(st.session_state['portfolio'])

    # Visualization: Portfolio Allocation Pie Chart
    fig = px.pie(
        st.session_state['portfolio'],
        values='Value',
        names='Token',
        title="Portfolio Allocation by Value"
    )
    st.plotly_chart(fig)

# Portfolio Insights
st.subheader("Portfolio Insights")
if not st.session_state['portfolio'].empty:
    total_value = st.session_state['portfolio']['Value'].sum()
    st.metric(label="Total Portfolio Value (USD)", value=f"${total_value:,.2f}")
