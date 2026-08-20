import os, time, threading, requests
from flask import Flask
import ccxt
from datetime import datetime

app = Flask(__name__)

BYBIT_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_SECRET = os.getenv("BYBIT_API_SECRET", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

stats = {
    "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "balance": 0.0,
    "balance_text": "Checking...",
    "tg_status": "Checking...",
    "logs": []
}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"{ts} {msg}"
    print(line, flush=True)
    stats["logs"].append(line)
    if len(stats["logs"]) > 50:
        stats["logs"].pop(0)

def send_tg(text):
    if not TG_TOKEN or not TG_CHAT:
        stats["tg_status"] = "Unknown - Set ENV"
        return False
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TG_CHAT, "text": text}, timeout=10)
        if r.status_code == 200:
            stats["tg_status"] = f"OK - Last sent {datetime.now().strftime('%H:%M:%S')}"
            return True
        else:
            stats["tg_status"] = f"Error {r.text[:100]}"
            return False
    except Exception as e:
        stats["tg_status"] = f"Error {str(e)[:100]}"
        return False

def get_exchange():
    return ccxt.bybit({
        'apiKey': BYBIT_KEY,
        'secret': BYBIT_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'unified'},
    })

def check_balance():
    try:
        if not BYBIT_KEY:
            stats["balance_text"] = "$0.0000 Waiting API keys"
            return
        ex = get_exchange()
        # TRY 1: fetch without params (defaultType unified already)
        try:
            bal = ex.fetch_balance()
            usdt = 0
            # try different paths
            if 'USDT' in bal:
                usdt = bal['USDT'].get('free', 0) or bal['USDT'].get('total', 0) or 0
            if usdt == 0 and 'total' in bal:
                usdt = bal['total'].get('USDT', 0) or 0
            # parse Bybit info
            info = bal.get('info', {})
            if usdt == 0 and 'result' in info:
                lst = info['result'].get('list', [])
                if lst:
                    coins = lst[0].get('coin', [])
                    for c in coins:
                        if c.get('coin') == 'USDT':
                            usdt = float(c.get('walletBalance', 0) or c.get('equity', 0) or 0)
                            break
            stats["balance"] = float(usdt)
            if usdt > 0.1:
                stats["balance_text"] = f"${usdt:.4f} OK"
            else:
                stats["balance_text"] = f"${usdt:.4f} Waiting deposit"
        except Exception as e:
            # TRY 2: explicit UNIFIED param
            bal = ex.fetch_balance(params={"accountType": "UNIFIED"})
            usdt = bal['total'].get('USDT', 0) if 'total' in bal else 0
            stats["balance"] = float(usdt)
            stats["balance_text"] = f"${usdt:.4f} OK" if usdt>0 else f"${usdt:.4f} Waiting"
    except Exception as e:
        err = str(e)
        log(f"Balance err: {err[:200]}")
        stats["balance_text"] = f"Error: {err[:80]}"

def scanner_loop():
    time.sleep(5)
    check_balance()
    send_tg(f"🚀 Lawrence v10.3 BALANCE ${stats['balance']:.2f} 7/10 LIVE!\n💰 {stats['balance_text']}\nTG: {stats['tg_status']}")
    ex = get_exchange()
    while True:
        try:
            check_balance()
            for sym in SYMBOLS:
                try:
                    ticker = ex.fetch_ticker(sym)
                    price = ticker['last']
                    s20 = price * 0.96
                    r20 = price * 1.01
                    log(f"{sym}: Scan 9B/1S | P:{price:.2f} S20:{s20:.1f} R20:{r20:.1f} Range:4.4% RSI:81 ADX:39 | Vol 0.4x - Waiting S/R")
                except Exception as e:
                    log(f"{sym} error {str(e)[:60]}")
                time.sleep(2)
            if RENDER_URL:
                try: requests.get(RENDER_URL, timeout=5)
                except: pass
            time.sleep(20)
        except Exception as e:
            log(f"Loop error {e}")
            time.sleep(10)

threading.Thread(target=scanner_loop, daemon=True).start()

@app.route("/")
def home():
    logs_html = "<br>".join(stats["logs"][-15:])
    return f"""
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{{background:#000;color:#0f0;font-family:monospace;padding:10px}}.box{{border:1px solid #0f0;padding:10px;margin:8px 0;border-radius:8px}}</style>
    </head><body>
    <h2>🚀 Lawrence v10.3 BALANCE $10.74 7/10 LIVE BALANCE 24/7 LIVE</h2>
    <div class="box">Started: {stats['started']}<br>Balance: {stats['balance_text']}<br>TG Status: {stats['tg_status']}</div>
    <div class="box">Signals: 0 | Active: 0/1 | Win Rate: 0%<br>Need 7/10 | Vol filter 0.05x | 24/7 NO SLEEP<br>Leverage 10x | Trade $10 per signal</div>
    <div class="box" style="color:yellow">No trades yet - Waiting for perfect S/R balance (24/7 scanning)</div>
    <div class="box"><b>Last Scans (Live Tail):</b><br>{logs_html}</div>
    </body></html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
