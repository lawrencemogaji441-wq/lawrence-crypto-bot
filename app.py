import os, time, threading, requests
from flask import Flask, request
import ccxt
from datetime import datetime

app = Flask(__name__)
BYBIT_KEY = (os.getenv("BYBIT_API_KEY") or "").strip()
BYBIT_SECRET = (os.getenv("BYBIT_API_SECRET") or "").strip()
TG_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TEL...") or os.getenv("BOT...") or "").strip()
TG_CHAT = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHA...") or "").strip().replace(" ","")

stats = {"started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "balance": "$10.74", "tg": "OK", "logs": [], "wins": 0, "losses": 0, "trades": [], "active": []}

def log(m):
    print(m, flush=True)
    stats["logs"].append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(stats["logs"])>15: stats["logs"].pop(0)

def send_tg(text):
    try:
        if not TG_TOKEN or not TG_CHAT: return
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT, "text": text}, timeout=10)
    except: pass

def ema(prices, period):
    # simple EMA
    k = 2/(period+1)
    ema_val = prices[0]
    for p in prices[1:]:
        ema_val = p*k + ema_val*(1-k)
    return ema_val

def get_signal(symbol, ex):
    try:
        ohlcv = ex.fetch_ohlcv(symbol, '1m', limit=50)
        closes = [c[4] for c in ohlcv]
        if len(closes)<30: return None
        ema7 = ema(closes[-7:], 7)
        ema25 = ema(closes[-25:], 25)
        ema7_prev = ema(closes[-8:-1], 7)
        ema25_prev = ema(closes[-26:-1], 25)
        # simple RSI calc
        gains = []
        losses = []
        for i in range(1,15):
            diff = closes[-i]-closes[-i-1]
            if diff>0: gains.append(diff)
            else: losses.append(abs(diff))
        rsi = 100 - (100/(1+ (sum(gains)/14)/(sum(losses)/14+0.001)))
        price = closes[-1]
        if ema7_prev < ema25_prev and ema7 > ema25 and rsi>50:
            return {"side":"Buy","symbol":symbol,"entry":price,"tp":price*1.03,"sl":price*0.985,"rsi":rsi}
        if ema7_prev > ema25_prev and ema7 < ema25 and rsi<50:
            return {"side":"Sell","symbol":symbol,"entry":price,"tp":price*0.97,"sl":price*1.015,"rsi":rsi}
    except Exception as e:
        log(f"Sig err {e}")
    return None

def worker():
    time.sleep(5)
    log("v11.5 LIGHT WIN TRACKER LIVE")
    send_tg(f"🚀 Lawrence v11.5 LIGHT LIVE ✅\nWin Rate Tracker ON\nBalance {stats['balance']}\nDashboard: https://e-crypto-bot.onrender.com/stats")
    ex = ccxt.bybit({'apiKey': BYBIT_KEY, 'secret': BYBIT_SECRET, 'enableRateLimit': True})
    while True:
        try:
            # check active
            for trade in stats["active"][:]:
                try:
                    price = ex.fetch_ticker(trade["symbol"])['last']
                    win=False; loss=False
                    if trade["side"]=="Buy":
                        if price>=trade["tp"]: win=True
                        if price<=trade["sl"]: loss=True
                    else:
                        if price<=trade["tp"]: win=True
                        if price>=trade["sl"]: loss=True
                    if win or loss:
                        stats["active"].remove(trade)
                        if win:
                            stats["wins"]+=1
                            send_tg(f"✅ WIN {trade['symbol']} {trade['side']}\n+3.0%")
                        else:
                            stats["losses"]+=1
                            send_tg(f"❌ LOSS {trade['symbol']} {trade['side']}\n-1.5%")
                        trade["result"]="WIN" if win else "LOSS"
                        stats["trades"].append(trade)
                except: pass
            # new signals
            for sym in ["BTCUSDT","ETHUSDT","SOLUSDT"]:
                sig = get_signal(sym, ex)
                if sig and len(stats["active"])<3:
                    if not any(t["symbol"]==sym and abs(time.time()-t["time"])<600 for t in stats["active"]):
                        sig["time"]=time.time()
                        sig["time_str"]=datetime.now().strftime("%H:%M")
                        stats["active"].append(sig)
                        send_tg(f"{'🟢' if sig['side']=='Buy' else '🔴'} {sig['side']} {sym} @ {sig['entry']:.2f}\nRSI {sig['rsi']:.1f}\n🎯 TP: {sig['tp']:.2f} (+3%) | 🛑 SL: {sig['sl']:.2f} (-1.5%)\n⏳ Tracking WIN/LOSS...")
                        log(f"New {sym}")
            # balance
            try:
                bal = ex.fetch_balance(params={"accountType":"UNIFIED"})
                for lst in bal.get('info',{}).get('result',{}).get('list',[]):
                    for c in lst.get('coin',[]):
                        if c['coin']=='USDT': stats["balance"]=f"${float(c['walletBalance']):.4f}"
            except: pass
        except Exception as e:
            log(f"Loop {e}")
        time.sleep(30)

threading.Thread(target=worker, daemon=True).start()

@app.route("/")
def home():
    total=stats["wins"]+stats["losses"]
    wr=(stats["wins"]/total*100) if total>0 else 0
    active="<br>".join([f"{t['time_str']} {t['side']} {t['symbol']} @ {t['entry']:.2f}" for t in stats["active"]]) or "None"
    return f"<html><body style='background:#000;color:#0f0;font-family:monospace;padding:15px'><h2>v11.5 LIGHT LIVE ✅</h2>Balance: {stats['balance']}<br>Win: {stats['wins']} Loss: {stats['losses']} WR: {wr:.1f}%<br><a href='/stats' style='color:#0ff'>📊 STATS</a><br><br>Active:<br>{active}<br><br>{'<br>'.join(stats['logs'][-10:])}</body></html>"

@app.route("/stats")
def stats_page():
    total=stats["wins"]+stats["losses"]
    wr=(stats["wins"]/total*100) if total>0 else 0
    profit=stats["wins"]*3 - stats["losses"]*1.5
    html_trades="".join([f"<div style='border:1px solid {'#0f0' if t['result']=='WIN' else '#f00'};padding:5px;margin:3px'>{t['result']} {t['symbol']} {t['side']}</div>" for t in reversed(stats["trades"][-20:])])
    return f"<html><body style='background:#000;color:#fff;font-family:monospace;padding:15px'><h2>📊 Win Rate</h2>Wins: {stats['wins']} Loss: {stats['losses']}<br>WR: {wr:.1f}%<br>Est Profit: {profit:.1f}%<br>Balance: {stats['balance']}<br><br>{html_trades}</body></html>"

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))    
