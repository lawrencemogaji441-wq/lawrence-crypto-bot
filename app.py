
            
            
                                    
# Lawrence v8 SNIPER 70% - Bybit LIVE FULL AUTO - FINAL
# FULL AUTO TRADING - REAL MONEY
import os, time, requests, pandas as pd, ta, pytz
from datetime import datetime
from pybit.unified_trading import HTTP

# === LIVE CONFIG ===
BYBIT_API_KEY = "PUT_YOUR_LIVE_KEY_HERE"
BYBIT_API_SECRET = "PUT_YOUR_LIVE_SECRET_HERE"
TELEGRAM_BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "PUT_YOUR_CHAT_ID_HERE"

SYMBOLS = ["BTCUSDT", "ETHUSDT"] # START WITH 1 OR 2 ONLY
CATEGORY = "linear"
QTY_USDT = 10  # Trade with $10 per signal, not qty coin - safer
LEVERAGE = "10"
STOP_LOSS_PCT = 1.5  # 1.5% SL
TAKE_PROFIT_PCT = 3.0 # 3% TP = 1:2 RR

WAT = pytz.timezone("Africa/Lagos")
bybit = HTTP(testnet=False, api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET)

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except: pass
    print(msg)

def get_candles(symbol, interval, limit=100):
    resp = bybit.get_kline(category=CATEGORY, symbol=symbol, interval=str(interval), limit=limit)
    df = pd.DataFrame(resp['result']['list'], columns=["startTime","open","high","low","close","volume","turnover"])
    df = df.iloc[::-1]
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

def calc_qty(symbol, price):
    # Convert $10 to coin qty
    try:
        info = bybit.get_instruments_info(category=CATEGORY, symbol=symbol)
        # simple: qty = USDT / price
        qty = QTY_USDT / price
        return str(round(qty, 3))
    except:
        return "0.01"

def check_v8(df_1m, df_5m):
    now = datetime.now(WAT)
    if not (7 <= now.hour < 21):
        return None, f"Outside 07-21 WAT {now.strftime('%H:%M')}"

    c = df_1m["close"]
    ema7, ema21, ema50 = ta.trend.ema_indicator(c,7).iloc[-1], ta.trend.ema_indicator(c,21).iloc[-1], ta.trend.ema_indicator(c,50).iloc[-1]
    rsi = ta.momentum.rsi(c,14).iloc[-1]
    
    c5 = df_5m["close"]
    ema7_5, ema21_5 = ta.trend.ema_indicator(c5,7).iloc[-1], ta.trend.ema_indicator(c5,21).iloc[-1]
    
    price = c.iloc[-1]
    if df_1m.iloc[-1]["high"] == df_1m.iloc[-1]["low"]:
        return None, "Volatility filter block"

    buy_cond = ema7 > ema21 > ema50 and price > ema7 and (ta.trend.ema_indicator(c,7).iloc[-2] > ta.trend.ema_indicator(c,21).iloc[-2]) and ema7_5 > ema21_5 and 52 <= rsi <= 68
    sell_cond = ema7 < ema21 < ema50 and price < ema7 and (ta.trend.ema_indicator(c,7).iloc[-2] < ta.trend.ema_indicator(c,21).iloc[-2]) and ema7_5 < ema21_5 and 32 <= rsi <= 48

    if buy_cond:
        return "Buy", f"BUY {price} EMA {ema7:.1f}>{ema21:.1f}>{ema50:.1f} RSI {rsi:.1f} 1m+5m OK"
    if sell_cond:
        return "Sell", f"SELL {price} EMA {ema7:.1f}<{ema21:.1f}<{ema50:.1f} RSI {rsi:.1f} 1m+5m OK"
    return None, f"Wait EMA7 {ema7:.1f} EMA21 {ema21:.1f} RSI {rsi:.1f}"

def place_auto_order(symbol, side, price):
    try:
        qty = calc_qty(symbol, price)
        # Set leverage
        try: bybit.set_leverage(category=CATEGORY, symbol=symbol, buyLeverage=LEVERAGE, sellLeverage=LEVERAGE)
        except: pass
        
        sl_price = price * (1 - STOP_LOSS_PCT/100) if side=="Buy" else price * (1 + STOP_LOSS_PCT/100)
        tp_price = price * (1 + TAKE_PROFIT_PCT/100) if side=="Buy" else price * (1 - TAKE_PROFIT_PCT/100)
        
        order = bybit.place_order(
            category=CATEGORY,
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            stopLoss=str(round(sl_price,2)),
            takeProfit=str(round(tp_price,2)),
            tpslMode="Full"
        )
        return True, order
    except Exception as e:
        return False, str(e)

def run():
    send_tg("🚀 Lawrence v8 SNIPER Bybit LIVE AUTO Started!
$10/order | Lev 10x | SL 1.5% TP 3% | 07-21 WAT | AUTO TRADING REAL MONEY")
    while True:
        for sym in SYMBOLS:
            try:
                df1 = get_candles(sym, 1)
                df5 = get_candles(sym, 5)
                sig, reason = check_v8(df1, df5)
                print(f"{datetime.now(WAT).strftime('%H:%M:%S')} {sym} {reason}")
                if sig:
                    price = df1["close"].iloc[-1]
                    send_tg(f"{'🟢' if sig=='Buy' else '🔴'} {sig} {sym} NOW @ {price}
{reason}
Placing LIVE order...")
                    ok, res = place_auto_order(sym, sig, price)
                    if ok:
                        send_tg(f"✅ AUTO EXECUTED {sym} {sig} Qty ${QTY_USDT} SL {STOP_LOSS_PCT}% TP {TAKE_PROFIT_PCT}%")
                    else:
                        send_tg(f"❌ FAILED {sym}: {res}")
                    time.sleep(300) # 5 min cooldown
            except Exception as e:
                print(f"Err {sym} {e}")
        time.sleep(30)

if __name__ == "__main__":
    run()
            
