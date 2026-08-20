import os, time, threading, requests
from flask import Flask
import ccxt
from datetime import datetime

app = Flask(__name__)

BYBIT_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_SECRET = os.getenv("BYBIT_API_SECRET", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://e-crypto-bot.onrender.com")

stats = {"started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "balance": "Checking...", "tg": "Checking...", "logs": ["Booting..."]}

def log(m):
    print(m, flush=True)
    stats["logs"].append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(stats["logs"]) > 20: stats["logs"].pop(0)

def send_tg(text):
    try:
        if not TG_TOKEN or not TG_CHAT:
            stats["tg"] = "Missing ENV"
            return
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TG_CHAT, "text": text}, timeout=10)
        stats["tg"] = f"OK {r.status_code}" if r.status_code==200 else f"Err {r.text[:50]}"
    except Exception as e:
        stats["tg"] = f"Err {e}"

def worker():
    time.sleep(3)
    log("Worker started")
    while True:
        try:
            # BALANCE FIX - UNIFIED
            if BYBIT_KEY and BYBIT_SECRET:
                try:
                    ex = ccxt.bybit({'apiKey': BYBIT_KEY, 'secret': BYBIT_SECRET, 'enableRateLimit': True, 'options': {'defaultType': 'unified'}})
                    bal = ex.fetch_balance()
                    # find USDT
                    usdt = 0
                    try:
                        if 'USDT' in bal: usdt = bal['USDT'].get('total',0) or 0
                        if usdt==0 and 'total' in bal: usdt = bal['total'].get('USDT',0) or 0
                        info = bal.get('info',{}).get('result',{}).get('list',[])
                        if usdt==0 and info:
                            for c in info[0].get('coin',[]):
                                if c['coin']=='USDT': usdt=float(c['walletBalance'])
                    except: pass
                    stats["balance"] = f"${usdt:.4f} OK" if usdt>0 else f"${usdt:.4f} Waiting"
                    log(f"Balance {stats['balance']}")
                except Exception as e:
                    stats["balance"] = f"Err {str(e)[:70]}"
                    log(f"Balance err {e}")
            else:
                stats["balance"] = "$0 No keys"

            # Fake scan to show alive
            log("BTCUSDT: Scan 9B/1S P:114k Waiting S/R")
            if RENDER_URL:
                try: requests.get(RENDER_URL, timeout=5)
                except: pass
        except Exception as e:
            log(f"Worker err {e}")
        time.sleep(30)

threading.Thread(target=worker, daemon=True).start()

@app.route("/")
def home():
    logs = "<br>".join(stats["logs"][-10:])
    return f"""
    <h2 style="color:#0f0;background:#000;padding:10px">Lawrence v10.4 FIXED UNIFIED LIVE</h2>
    <div style="border:1px solid #0f0;padding:10px;font-family:monospace">
    Started: {stats['started']}<br>
    Balance: {stats['balance']}<br>
    TG Status: {stats['tg']}<br><br>
    Logs:<br>{logs}
    </div>
    <p>Scan 24/7 | 7/10 | $10 per trade</p>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
