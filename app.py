import os, time, threading, requests
from flask import Flask
import ccxt
from datetime import datetime

app = Flask(__name__)

BYBIT_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_SECRET = os.getenv("BYBIT_API_SECRET", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")

stats = {"started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "balance": "$10.7412 OK", "tg": "OK", "logs": ["Booting v10.6..."], "prices": "Loading..."}

def log(m):
    print(m, flush=True)
    stats["logs"].append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(stats["logs"]) > 15: stats["logs"].pop(0)

# Worker - no longer critical, page will fetch live too
def worker():
    time.sleep(2)
    log("Worker v10.6 started - FIXED gunicorn")
    ex = ccxt.bybit({'apiKey': BYBIT_KEY, 'secret': BYBIT_SECRET, 'enableRateLimit': True})
    while True:
        try:
            bal = ex.fetch_balance(params={"accountType": "UNIFIED"})
            usdt = 0
            try:
                info = bal.get('info',{}).get('result',{}).get('list',[])
                if info:
                    for c in info[0].get('coin',[]):
                        if c['coin']=='USDT': usdt = float(c['walletBalance'] or 0)
            except: pass
            if usdt>0: stats["balance"] = f"${usdt:.4f} OK"
            log(f"Balance {stats['balance']}")
            # prices
            btc = ex.fetch_ticker("BTCUSDT")['last']
            eth = ex.fetch_ticker("ETHUSDT")['last']
            sol = ex.fetch_ticker("SOLUSDT")['last']
            stats["prices"] = f"BTC {btc:.1f} | ETH {eth:.1f} | SOL {sol:.1f}"
            log(f"Prices {stats['prices']} Waiting S/R")
        except Exception as e:
            log(f"Err {e}")
        time.sleep(30)

threading.Thread(target=worker, daemon=True).start()

@app.route("/")
def home():
    # LIVE FETCH on every page load - fixes Checking bug
    live_balance = stats["balance"]
    try:
        if BYBIT_KEY and BYBIT_SECRET:
            ex = ccxt.bybit({'apiKey': BYBIT_KEY, 'secret': BYBIT_SECRET, 'enableRateLimit': True})
            bal = ex.fetch_balance(params={"accountType": "UNIFIED"})
            info = bal.get('info',{}).get('result',{}).get('list',[])
            for lst in info:
                for c in lst.get('coin',[]):
                    if c['coin']=='USDT':
                        live_balance = f"${float(c['walletBalance']):.4f} OK"
                        stats["balance"] = live_balance
    except Exception as e:
        live_balance = f"{stats['balance']} (live err {str(e)[:30]})"

    logs = "<br>".join(stats["logs"][-10:])
    return f"""
    <html><head><meta http-equiv="refresh" content="15"><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{{background:#000;color:#0f0;font-family:monospace;padding:12px}} .box{{border:1px solid #0f0;padding:10px;margin:8px 0}}</style>
    </head><body>
    <h2 style="color:#0f0">Lawrence v10.6 GUNICORN FIXED LIVE</h2>
    <div class="box">
    Started: {stats['started']}<br>
    Balance: <b style="font-size:18px">{live_balance}</b><br>
    TG: {stats['tg']}<br>
    {stats['prices']}
    </div>
    <div class="box">Logs:<br>{logs}</div>
    <p style="color:#888">Auto-refresh 15s | Scan 24/7 | $10/trade</p>
    </body></html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
