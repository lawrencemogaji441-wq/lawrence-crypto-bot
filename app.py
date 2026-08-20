import os, time, threading, requests
from flask import Flask, request
import ccxt
from datetime import datetime

app = Flask(__name__)
BYBIT_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_SECRET = os.getenv("BYBIT_API_SECRET", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
stats = {"started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "balance": "$10.74 OK", "tg": "Checking...", "logs": ["Booting v10.7.1..."], "prices": "Loading..."}

def log(m):
    print(m, flush=True)
    stats["logs"].append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(stats["logs"]) > 15: stats["logs"].pop(0)

def send_tg(text):
    try:
        if not TG_TOKEN or not TG_CHAT: stats["tg"]="Missing ENV"; return False
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TG_CHAT, "text": text}, timeout=15)
        stats["tg"] = "OK" if r.status_code==200 else f"Err {r.text[:80]}"
        log(f"TG {stats['tg']}")
        return r.status_code==200
    except Exception as e: stats["tg"]=f"Err {e}"; log(f"TG Ex {e}"); return False

def worker():
    time.sleep(3)
    log("Worker v10.7.1 TG fix")
    send_tg(f"🤖 Lawrence Bot v10.7.1 LIVE\n💰 {stats['balance']}\n🕐 {stats['started']}\nScanning 24/7")
    ex = ccxt.bybit({'apiKey': BYBIT_KEY, 'secret': BYBIT_SECRET, 'enableRateLimit': True})
    while True:
        try:
            bal = ex.fetch_balance(params={"accountType": "UNIFIED"})
            for lst in bal.get('info',{}).get('result',{}).get('list',[]):
                for c in lst.get('coin',[]):
                    if c['coin']=='USDT': stats["balance"]=f"${float(c['walletBalance']):.4f} OK"
            stats["prices"]=f"BTC {ex.fetch_ticker('BTCUSDT')['last']:.0f} | ETH {ex.fetch_ticker('ETHUSDT')['last']:.0f}"
            log(f"{stats['prices']} Waiting")
        except Exception as e: log(f"Err {e}")
        time.sleep(40)

threading.Thread(target=worker, daemon=True).start()

@app.route("/")
def home():
    live = stats["balance"]
    if "test_tg" in request.args: send_tg("✅ TG Test OK - Bot is LIVE!")
    try:
        ex = ccxt.bybit({'apiKey': BYBIT_KEY, 'secret': BYBIT_SECRET, 'enableRateLimit': True})
        bal = ex.fetch_balance(params={"accountType": "UNIFIED"})
        for lst in bal.get('info',{}).get('result',{}).get('list',[]):
            for c in lst.get('coin',[]):
                if c['coin']=='USDT': live=f"${float(c['walletBalance']):.4f} OK"; stats["balance"]=live
    except: pass
    logs="<br>".join(stats["logs"][-12:])
    return f'<html><head><meta http-equiv="refresh" content="20"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{background:#000;color:#0f0;font-family:monospace;padding:12px}}.box{{border:1px solid #0f0;padding:10px;margin:8px 0}}a{{color:#0ff}}</style></head><body><h2>Lawrence v10.7.1 TG FIXED</h2><div class="box">Started: {stats["started"]}<br>Balance: <b>{live}</b><br>TG: {stats["tg"]}<br>{stats["prices"]}</div><div class="box"><a href="/?test_tg=1">👉 TEST Telegram NOW</a></div><div class="box">Logs:<br>{logs}</div></body></html>'

@app.route("/test-tg")
def test_tg():
    ok = send_tg("🧪 TG Test OK - If you see this TG works!")
    return f"TG Send: {ok} Status: {stats['tg']}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
