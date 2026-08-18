
    import os, time, requests, pandas as pd, ta, pytz, threading
from datetime import datetime
from pybit.unified_trading import HTTP
from flask import Flask, render_template_string

# ====== CONFIG FROM RENDER ENV VARIABLES ======
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "") or os.getenv("BOT_TOKEN","")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "") or os.getenv("CHAT_ID","")

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

stats = {
    "started_at": datetime.now(WAT).strftime("%Y-%m-%d %H:%M:%S"),
    "status": "Running",
    "mode": "LIVE AUTO" if BYBIT_API_KEY else "SIGNAL ONLY - Add BYBIT_API_KEY to trade LIVE",
    "total_signals": 0,
    "wins": 0,
    "losses": 0,
    "last_signal": "Bot starting...",
    "balance": "Connect API to see",
    "trades": []
}

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lawrence v8 - Performance</title>
<style>
body{font-family:Arial;background:#0a0a0a;color:#fff;margin:0;padding:15px}
.card{background:#1a1a1a;border-radius:12px;padding:15px;margin-bottom:15px;border:1px solid #333}
.green{color:#00ff88} .red{color:#ff4444} .yellow{color:#ffcc00}
h1{font-size:22px;margin:0 0 10px}
.metric{display:inline-block;width:48%;margin:8px 0}
.big{font-size:26px;font-weight:bold}
small{color:#888}
table{width:100%;border-collapse:collapse;margin-top:10px}
th,td{padding:8px;text-align:left;border-bottom:1px solid #333;font-size:13px}
.btn{display:inline-block;background:#ff9900;color:#000;padding:10px 15px;border-radius:8px;text-decoration:none;font-weight:bold;margin:5px 5px 0 0}
</style>
<meta http-equiv="refresh" content="15">
</head>
<body>
<h1>🚀 Lawrence v8 Sniper <span class="yellow">LIVE</span></h1>
<small>Started: {{started_at}} | WAT: {{now}} | Refresh 15s</small>

<div class="card">
<div class="metric"><small>Status</small><br><span class="green">{{status}}</span></div>
<div class="metric"><small>Mode</small><br>{{mode}}</div>
<div class="metric"><small>Total Signals</small><br><span class="big">{{total_signals}}</span></div>
<div class="metric"><small>Win Rate</small><br><span class="big green">{{winrate}}%</span></div>
<div class="metric"><small>Wins</small><br><span class="green">{{wins}}</span></div>
<div class="metric"><small>Losses</small><br><span class="red">{{losses}}</span></div>
</div>

<div class="card">
<h3>📡 Last Signal</h3>
<p style="font-size:13px;background:#222;padding:10px;border-radius:8px">{{last_signal}}</p>
<h3>💰 Balance</h3>
<p>{{balance}}</p>
</div>

<div class="card">
<h3>📊 Recent Trades</h3>
<table>
<tr><th>Time</th><th>Pair</th><th>Side</th><th>Result</th></tr>
{% for t in trades %}
<tr><td>{{t.time}}</td><td>{{t.pair}}</td><td>{{t.type}}</td><td class="{{t.cls}}">{{t.result}}</td></tr>
{% else %}
<tr><td colspan=4 style="text-align:center;color:#666">No trades yet - scanning for EMA7 cross</td></tr>
{% endfor %}
</table>
<div style="margin-top:15px">
<a class="btn" href="/api/performance" target="_blank">JSON API</a>
<a class="btn" href="https://dashboard.render.com" target="_blank">Render Logs</a>
</div>
</div>

<small style="display:block;text-align:center;margin-top:20px;color:#555">EMA7 Sniper • 07:00-21:00 WAT • SL 1.5% TP 3% • Lev 10x • Bybit Linear</small>
</body>
</html>
"""

def send_tg(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(msg); return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
    except Exception as e:
        print(f"TG Error {e}")
    print(msg)

def get_candles(symbol, interval, limit=100):
    if not bybit:
        # Signal only mode - use public API without auth
        public = HTTP(testnet=False)
        resp = public.get_kline(category=CATEGORY, symbol=symbol, interval=str(interval), limit=limit)
    else:
        resp = bybit.get_kline(category=CATEGORY, symbol=symbol, interval=str(interval), limit=limit)
    df = pd.DataFrame(resp['result']['list'], columns=["startTime","open","high","low","close","volume","turnover"])
    df = df.iloc[::-1]
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

def calc_qty(symbol, price):
    qty = QTY_USDT / price
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
    return None, f"Scanning EMA7 {ema7:.1f} EMA21 {ema21:.1f} RSI {rsi:.1f} @ {price:.2f}"

def place_auto_order(symbol, side, price):
    if not bybit:
        return False, "No API - Signal Only mode"
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
    send_tg("🚀 Lawrence v8 LIVE Started on Render!\nDashboard: https://lawrence-crypto-bot.onrender.com")
    while True:
        for sym in SYMBOLS:
            try:
                df1 = get_candles(sym, 1)
                df5 = get_candles(sym, 5)
                sig, reason = check_v8(df1, df5)
                stats["last_signal"] = f"{sym}: {reason}"
                print(f"{datetime.now(WAT).strftime('%H:%M:%S')} {sym} {reason}")
                if sig:
                    price = df1["close"].iloc[-1]
                    stats["total_signals"] += 1
                    trade = {"time": datetime.now(WAT).strftime("%H:%M:%S"), "pair": sym, "type": sig, "result": "Signal", "cls": "yellow"}
                    stats["trades"] = [trade] + stats["trades"][:9]
                    send_tg(f"{'🟢' if sig=='Buy' else '🔴'} {sig} {sym} @ {price:.2f}\n{reason}\nPlacing order...")
                    ok, res = place_auto_order(sym, sig, price)
                    if ok:
                        stats["wins"] += 1
                        trade["result"] = "EXECUTED ✅"
                        trade["cls"] = "green"
                    else:
                        if "Signal Only" in res:
                            trade["result"] = "SIGNAL ONLY (No API)"
                        else:
                            stats["losses"] += 1
                            trade["result"] = f"FAILED ❌ {res[:50]}"
                            trade["cls"] = "red"
                    send_tg(f"{'✅ AUTO EXECUTED' if ok else '⚠️'} {sym} {sig}: {res[:300]}")
                    time.sleep(300)
            except Exception as e:
                stats["last_signal"] = f"Error {sym}: {e}"
                print(f"Error {sym}: {e}")
                time.sleep(10)
        time.sleep(30)

@app.route('/')
def home():
    winrate = round((stats["wins"] / stats["total_signals"] * 100), 1) if stats["total_signals"]>0 else 0
    return render_template_string(DASHBOARD_HTML, winrate=winrate, now=datetime.now(WAT).strftime("%Y-%m-%d %H:%M:%S"), **stats)

@app.route('/api/performance')
def api_perf():
    return stats

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))

    
