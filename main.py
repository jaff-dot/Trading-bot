import time
import json
import requests
from binance.client import Client
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from ta.trend import MACD
import pandas as pd

# Load config
with open("config.json") as f:
    config = json.load(f)

client = Client(config["binance_api"], config["binance_secret"])
symbol = "BTCUSDT"
quantity = 10
interval = "15m"

def get_klines(symbol, interval, limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close", "volume", "close_time",
                                       "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume",
                                       "taker_buy_quote_asset_volume", "ignore"])
    df["close"] = pd.to_numeric(df["close"])
    return df

def calculate_indicators(df):
    bb = BollingerBands(close=df["close"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["rsi"] = RSIIndicator(close=df["close"], window=14).rsi()
    macd = MACD(close=df["close"])
    df["macd_diff"] = macd.macd_diff()
    return df

def send_telegram(message):
    url = f"https://api.telegram.org/bot{config['telegram_token']}/sendMessage"
    data = {"chat_id": config["telegram_chat_id"], "text": message}
    requests.post(url, data=data)

def place_order(side):
    try:
        order = client.create_test_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity
        )
        send_telegram(f"{side} order placed successfully: {order}")
    except Exception as e:
        send_telegram(f"Order failed: {e}")

def run_bot():
    df = get_klines(symbol, interval)
    df = calculate_indicators(df)
    latest = df.iloc[-1]
    if latest["close"] < latest["bb_lower"] and latest["rsi"] < 30 and latest["macd_diff"] > 0:
        place_order("BUY")
    elif latest["close"] > latest["bb_upper"] and latest["rsi"] > 70 and latest["macd_diff"] < 0:
        place_order("SELL")

while True:
    run_bot()
    time.sleep(60 * 15)
