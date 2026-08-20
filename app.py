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

stats = {"started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "balance": "Checking...", "tg": "Checking...", "logs": ["Booting v10.5..."]}

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
    log("Worker v10.5 started - FIXED unified bug")
    ex = ccxt.bybit({'apiKey': BYBIT_KEY, 'secret': BYBIT_SECRET, 'enableRateLimit': True})
    while True:
        try:
            if BYBIT_KEY:
                try:
                    bal = ex.fetch_balance(params={"accountType": "UNIFIED"})
                    usdt = 0
                    if 'USDT' in bal: usdt = bal['USDT'].get('total',0) or 0
                    if usdt==0 and 'total' in bal: usdt = bal['total'].get('USDT',0) or 0
                    # parse Bybit raw
                    try:
                        info = bal.get('info',{}).get('result',{}).get('list',[])
                        if info:
                            for c in info[0].get('coin',[]):
                                if c['coin']=='USDT':
                                    usdt = float(c['walletBalance'] or c['equity'] or 0)
                    except: pass
                    stats["balance"] = f"${usdt:.4f} OK" if usdt>0.1 else f"${usdt:.4f} Waiting"
                    log(f"Balance {stats['balance']}")
                except Exception as e:
                    stats["balance"] = f"Err {str(e)[:80]}"
                    log(f"Balance err {e}")

            # scan without unified param
            for sym in ["BTCUSDT","ETHUSDT","SOLUSDT"]:
                try:
                    ticker = ex.fetch_ticker(sym)
                    log(f"{sym}: Scan 9B/1S P:{ticker['last']:.1f} Waiting S/R")
                except Exception as e:
                    log(f"{sym} ticker err {e}")

            try:
                if RENDER_URL: requests.get(RENDER_URL, timeout=5)
            except: pass
        except Exception as e:
            log(f"Loop err {e}")
        time.sleep(25)

threading.Thread(target=worker, daemon=True).start()

@app.route("/")
def home():
    logs = "<br>".join(stats["logs"][-12:])
    return f"""
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{{background:#000;color:#0f0;font-family:monospace;padding:10px}}.box{{border:1px solid #0f0;padding:10px;margin:8px 0}}</style>
    </head><body>
    <h2>Lawrence v10.5 UNIFIED FIXED LIVE</h2>
    <div class="box">Started: {stats['started']}<br>Balance: {stats['balance']}<br>TG: {stats['tg']}</div>
    <div class="box">{logs}</div>
    </body></html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
