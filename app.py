
import os, time, requests, pandas as pd, ta, pytz, threading
from datetime import datetime
from pybit.unified_trading import HTTP
from flask import Flask

# ====== CONFIG FROM RENDER ENV VARIABLES ======
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
CATEGORY = "linear"
QTY_USDT = 10
LEVERAGE = "10"
STOP_LOSS_PCT = 1.5
TAKE_PROFIT_PCT = 3.0
WAT = pytz.timezone("Africa/Lagos")

bybit = None
if BYBIT_API_KEY and BYBIT_API_SECRET:
    bybit = HTTP(testnet=False, api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET)

app = Flask(__name__)

def send_tg(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(msg)
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
    except Exception as e:
        print(f"TG Error {e}")
    print(msg)

def get_candles(symbol, interval, limit=100):
    if not bybit:
        raise Exception("BYBIT keys not set in ENV")
    resp = bybit.get_kline(category=CATEGORY, symbol=symbol, interval=str(interval), limit=limit)
    df = pd.DataFrame(resp['result']['list'], columns=["startTime","open","high","low","close","volume","turnover"])
    df = df.iloc[::-1]
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

def calc_qty(symbol, price):
    qty = QTY_USDT / price
    # round to 3 decimals for BTC
    return str(round(qty, 3)) if price > 100 else str(round(qty, 2))

def check_v8(df_1m, df_5m):
    now = datetime.now(WAT)
    if not (7 <= now.hour < 21):
        return None, f"Sleep - Outside 07-21 WAT {now.strftime('%H:%M')}"
    c = df_1m["close"]
    if len(c) < 60:
        return None, "Not enough candles"
    ema7, ema21, ema50 = ta.trend.ema_indicator(c,7).iloc[-1], ta.trend.ema_indicator(c,21).iloc[-1], ta.trend.ema_indicator(c,50).iloc[-1]
    rsi = ta.momentum.rsi(c,14).iloc[-1]
    c5 = df_5m["close"]
    ema7_5, ema21_5 = ta.trend.ema_indicator(c5,7).iloc[-1], ta.trend.ema_indicator(c5,21).iloc[-1]
    price = c.iloc[-1]
    if df_1m.iloc[-1]["high"] == df_1m.iloc[-1]["low"]:
        return None, "Volatility filter"
    buy_cond = ema7 > ema21 > ema50 and price > ema7 and ema7_5 > ema21_5 and 52 <= rsi <= 68
    sell_cond = ema7 < ema21 < ema50 and price < ema7 and ema7_5 < ema21_5 and 32 <= rsi <= 48
    if buy_cond:
        return "Buy", f"BUY Price {price:.2f} EMA7 {ema7:.2f}>{ema21:.2f}>{ema50:.2f} RSI {rsi:.1f} 1m+5m OK"
    if sell_cond:
        return "Sell", f"SELL Price {price:.2f} EMA7 {ema7:.2f}<{ema21:.2f}<{ema50:.2f} RSI {rsi:.1f} 1m+5m OK"
    return None, f"Scanning EMA7 {ema7:.1f} EMA21 {ema21:.1f} RSI {rsi:.1f}"

def place_auto_order(symbol, side, price):
    try:
        qty = calc_qty(symbol, price)
        try: bybit.set_leverage(category=CATEGORY, symbol=symbol, buyLeverage=LEVERAGE, sellLeverage=LEVERAGE)
        except: pass
        sl = price * (1 - STOP_LOSS_PCT/100) if side=="Buy" else price * (1 + STOP_LOSS_PCT/100)
        tp = price * (1 + TAKE_PROFIT_PCT/100) if side=="Buy" else price * (1 - TAKE_PROFIT_PCT/100)
        order = bybit.place_order(category=CATEGORY, symbol=symbol, side=side, orderType="Market", qty=qty, stopLoss=str(round(sl,2)), takeProfit=str(round(tp,2)), tpslMode="Full")
        return True, str(order)
    except Exception as e:
        return False, str(e)

def bot_loop():
    send_tg("🚀 Lawrence v8 SNIPER 70% LIVE AUTO Started on Render!
Auto trading Bybit REAL with $10/order Lev 10x SL 1.5% TP 3%")
    while True:
        for sym in SYMBOLS:
            try:
                df1 = get_candles(sym, 1)
                df5 = get_candles(sym, 5)
                sig, reason = check_v8(df1, df5)
                print(f"{datetime.now(WAT).strftime('%H:%M:%S')} {sym} {reason}")
                if sig:
                    price = df1["close"].iloc[-1]
                    send_tg(f"{'🟢' if sig=='Buy' else '🔴'} {sig} {sym} @ {price:.2f}\n{reason}\nPlacing LIVE order...")
                    ok, res = place_auto_order(sym, sig, price)
                    send_tg(f"{'✅ AUTO EXECUTED' if ok else '❌ FAILED'} {sym} {sig}: {res[:300]}")
                    time.sleep(300)
            except Exception as e:
                print(f"Error {sym}: {e}")
                time.sleep(10)
        time.sleep(30)

@app.route('/')
def home():
    return f"<h1>Lawrence v8 SNIPER LIVE AUTO</h1><p>Bybit LIVE Trading Active</p><p>Time WAT: {datetime.now(WAT).strftime('%Y-%m-%d %H:%M:%S')}</p><p>Symbols: {', '.join(SYMBOLS)}</p><p>Status: {'Keys OK' if bybit else 'ADD BYBIT KEYS IN RENDER ENV'}</p>"

# Start bot thread when Flask starts
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
    
