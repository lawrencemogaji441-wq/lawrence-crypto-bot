import os, time, threading, requests
from flask import Flask, request
import ccxt
from datetime import datetime

app = Flask(__name__)

# Try ALL possible names + strip spaces
def get_env(*names):
    for n in names:
        v = os.getenv(n, "")
        if v: 
            return v.strip()
    return ""

BYBIT_KEY = get_env("BYBIT_API_KEY", "BYB_API_KEY", "BYBIT_KEY", "BYB...") 
BYBIT_SECRET = get_env("BYBIT_API_SECRET", "BYBIT_SECRET", "BYB...")
TG_TOKEN = get_env("TELEGRAM_BOT_TOKEN", "TEL...", "BOT_TOKEN", "TELEGRAM_TOKEN", "TG_TOKEN", "BOT...").strip()
TG_CHAT = get_env("TELEGRAM_CHAT_ID", "CHA...", "CHAT_ID", "TG_CHAT_ID", "TELEGRAM_CHAT").strip()
# remove any spaces/newlines
TG_CHAT = TG_CHAT.replace(" ", "").replace("\n","")

stats = {"started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "balance": "$10.74 OK", "tg": "Checking...", "logs": ["Booting v10.8 fallback..."], "prices": "Loading...", "env": f"token={bool(TG_TOKEN)} chat={bool(TG_CHAT)}"}

def log(m):
    print(m, flush=True)
    stats["logs"].append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(stats["logs"])>15: stats["logs"].pop(0)

def send_tg(text):
    try:
        if not TG_TOKEN or not TG_CHAT:
            stats["tg"] = f"Missing token={bool(TG_TOKEN)} chat={bool(TG_CHAT)} lenT={len(TG_TOKEN)} lenC={len(TG_CHAT)}"
            log(stats["tg"])
            return False
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TG_CHAT, "text": text}, timeout=15)
        if r.status_code==200:
            stats["tg"] = "OK ✅"
            log("TG Sent OK")
            return True
        else:
            stats["tg"] = f"Err {r.status_code} {r.text[:150]}"
            log(stats["tg"])
            return False
    except Exception as e:
        stats["tg"] = f"Ex {e}"
        log(stats["tg"])
        return False

def worker():
    time.sleep(3)
    log(f"ENV CHECK -> token exists={bool(TG_TOKEN)} chat exists={bool(TG_CHAT)} token len {len(TG_TOKEN)}")
    log(f"Chat value preview: {TG_CHAT[:6]}...")
    send_tg(f"🤖 Lawrence v10.8 LIVE ✅\nBalance {stats['balance']}\n{stats['started']}\nTG Fixed with fallback!")
    ex = ccxt.bybit({'apiKey': BYBIT_KEY, 'secret': BYBIT_SECRET, 'enableRateLimit': True})
    while True:
        try:
            bal = ex.fetch_balance(params={"accountType": "UNIFIED"})
            for lst in bal.get('info',{}).get('result',{}).get('list',[]):
                for c in lst.get('coin',[]):
                    if c['coin']=='USDT':
                        stats["balance"] = f"${float(c['walletBalance']):.4f} OK"
            stats["prices"] = f"BTC {ex.fetch_ticker('BTCUSDT')['last']:.0f} | ETH {ex.fetch_ticker('ETHUSDT')['last']:.0f}"
            log(f"{stats['prices']} | {stats['balance']}")
        except Exception as e:
            log(f"Err {e}")
        time.sleep(40)

threading.Thread(target=worker, daemon=True).start()

@app.route("/")
def home():
    if "test_tg" in request.args:
        send_tg("✅ TEST Telegram - If you see this, TG works! Lawrence bot is LIVE")
    logs = "<br>".join(stats["logs"][-15:])
    # also try live balance fetch
    live = stats["balance"]
    return f"""<html><head><meta http-equiv="refresh" content="20"><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{{background:#000;color:#0f0;font-family:monospace;padding:12px}}.box{{border:1px solid #0f0;padding:10px;margin:8px 0}}a{{color:#0ff}}</style></head>
    <body><h2>Lawrence v10.8 FALLBACK FIXED</h2>
    <div class="box">Started: {stats['started']}<br>Balance: <b>{live}</b><br>TG: {stats['tg']}<br>ENV: {stats['env']}<br>Prices: {stats['prices']}</div>
    <div class="box"><a href="/?test_tg=1">👉 TEST Telegram NOW</a> | <a href="/debug">DEBUG ENV</a></div>
    <div class="box">Logs:<br>{logs}</div></body></html>"""

@app.route("/debug")
def debug():
    keys = list(os.environ.keys())
    # only show relevant keys
    rel = [k for k in keys if "BYB" in k or "TEL" in k or "BOT" in k or "CHA" in k or "TELE" in k]
    return f"All env keys containing BYB/TEL/BOT/CHA/TELE:<br>{'<br>'.join(rel)}<br><br>Parsed:<br>TG_TOKEN exists={bool(TG_TOKEN)} len={len(TG_TOKEN)} starts={TG_TOKEN[:4] if TG_TOKEN else 'none'}<br>TG_CHAT exists={bool(TG_CHAT)} len={len(TG_CHAT)} val={TG_CHAT}<br>BYBIT_KEY exists={bool(BYBIT_KEY)}<br>BYBIT_SECRET exists={bool(BYBIT_SECRET)}"

@app.route("/test-tg")
def test_tg():
    ok = send_tg("🧪 Direct /test-tg works!")
    return f"Sent={ok} -> {stats['tg']}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
