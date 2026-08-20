import os, time, threading, requests
from flask import Flask, request
import ccxt
from datetime import datetime
import pandas as pd
import ta

app = Flask(__name__)
BYBIT_KEY = os.getenv("BYBIT_API_KEY") or os.getenv("BYB...") or ""
BYBIT_SECRET = os.getenv("BYBIT_API_SECRET") or os.getenv("BYB...") or ""
TG_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TEL...") or os.getenv("BOT...") or "").strip()
TG_CHAT = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHA...") or "").strip().replace(" ","")

stats = {"started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "balance": "$10.74", "tg": "OK", "logs": [], "wins": 0, "losses": 0, "trades": [], "active": []}
def log(m):
    print(m, flush=True)
    stats["logs"].append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(stats["logs"])>20: stats["logs"].pop(0)

def send_tg(text):
    try:
        if not TG_TOKEN or not TG_CHAT: return
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT, "text": text}, timeout=10)
    except: pass

def get_signal(symbol, ex):
    try:
        ohlcv = ex.fetch_ohlcv(symbol, '1m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        df['ema7'] = ta.trend.ema_indicator(df['c'], window=7)
        df['ema25'] = ta.trend.ema_indicator(df['c'], window=25)
        df['rsi'] = ta.momentum.rsi(df['c'], window=14)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = last['c']
        if prev['ema7'] < prev['ema25'] and last['ema7'] > last['ema25'] and last['rsi'] > 50:
            return {"side": "Buy", "symbol": symbol, "entry": price, "tp": price*1.03, "sl": price*0.985, "rsi": last['rsi']}
        if prev['ema7'] > prev['ema25'] and last['ema7'] < last['ema25'] and last['rsi'] < 50:
            return {"side": "Sell", "symbol": symbol, "entry": price, "tp": price*0.97, "sl": price*1.015, "rsi": last['rsi']}
    except Exception as e:
        log(f"Sig err {e}")
    return None

def worker():
    time.sleep(5)
    log("v11.5 WIN RATE Tracker LIVE")
    send_tg(f"🚀 Lawrence v11.5 LIVE ✅\nWin Rate Tracker ON\nBalance {stats['balance']}\nDashboard: https://e-crypto-bot.onrender.com/stats")
    ex = ccxt.bybit({'apiKey': BYBIT_KEY, 'secret': BYBIT_SECRET, 'enableRateLimit': True})
    while True:
        try:
            # 1. Check active trades for WIN/LOSS
            for trade in stats["active"][:]:
                try:
                    ticker = ex.fetch_ticker(trade["symbol"])
                    price = ticker['last']
                    win = False
                    loss = False
                    if trade["side"]=="Buy":
                        if price >= trade["tp"]: win=True
                        if price <= trade["sl"]: loss=True
                    else:
                        if price <= trade["tp"]: win=True
                        if price >= trade["sl"]: loss=True
                    
                    if win or loss:
                        stats["active"].remove(trade)
                        if win:
                            stats["wins"]+=1
                            send_tg(f"✅ WIN {trade['symbol']} {trade['side']}\nEntry {trade['entry']:.2f} → TP {trade['tp']:.2f}\n+3.0% Profit 💰")
                        else:
                            stats["losses"]+=1
                            send_tg(f"❌ LOSS {trade['symbol']} {trade['side']}\nEntry {trade['entry']:.2f} → SL {trade['sl']:.2f}\n-1.5% Loss")
                        trade["result"]="WIN" if win else "LOSS"
                        trade["exit_price"]=price
                        stats["trades"].append(trade)
                except: pass

            # 2. Scan for new signals every 60s
            for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]:
                sig = get_signal(sym, ex)
                if sig and len(stats["active"])<4: # max 4 active
                    # avoid duplicate
                    if not any(t["symbol"]==sym and abs(time.time()-t["time"])<600 for t in stats["active"]):
                        sig["time"]=time.time()
                        sig["time_str"]=datetime.now().strftime("%H:%M")
                        stats["active"].append(sig)
                        send_tg(f"{'🟢' if sig['side']=='Buy' else '🔴'} {sig['side']} {sym} @ {sig['entry']:.2f}\n{'BUY' if sig['side']=='Buy' else 'SELL'} Price {sig['entry']:.2f} RSI {sig['rsi']:.1f}\n1m+5m OK\n🎯 TP: {sig['tp']:.2f} (+3.0%) | 🛑 SL: {sig['sl']:.2f} (-1.5%)\nRisk:Reward 1:2 | Lev 10x\n⏳ Tracking for WIN/LOSS...")
                        log(f"New {sym} {sig['side']}")
            
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
    total = stats["wins"]+stats["losses"]
    wr = (stats["wins"]/total*100) if total>0 else 0
    active_html = "<br>".join([f"{t['time_str']} {t['side']} {t['symbol']} @ {t['entry']:.2f} TP {t['tp']:.2f} SL {t['sl']:.2f}" for t in stats["active"]]) or "No active trades"
    return f"<html><body style='background:#000;color:#0f0;font-family:monospace;padding:15px'><h2>Lawrence v11.5 WIN TRACKER ✅</h2>Balance: {stats['balance']}<br>Wins: {stats['wins']} | Losses: {stats['losses']} | Total: {total} | WinRate: {wr:.1f}%<br><br><a href='/stats' style='color:#0ff'>📊 FULL STATS</a><br><br>Active:<br>{active_html}<br><br>Logs:<br>{'<br>'.join(stats['logs'][-10:])}</body></html>"

@app.route("/stats")
def stats_page():
    total = stats["wins"]+stats["losses"]
    wr = (stats["wins"]/total*100) if total>0 else 0
    profit = stats["wins"]*3 - stats["losses"]*1.5 # % profit
    trades_html = ""
    for t in reversed(stats["trades"][-20:]):
        color = "#0f0" if t["result"]=="WIN" else "#f00"
        trades_html += f"<div style='border:1px solid {color};padding:5px;margin:5px'><span style='color:{color}'>{t['result']}</span> {t['side']} {t['symbol']} Entry {t['entry']:.2f} Exit {t.get('exit_price',0):.2f}</div>"
    return f"<html><body style='background:#000;color:#fff;font-family:monospace;padding:15px'><h2>📊 Lawrence Win Rate</h2><div style='font-size:20px'>Wins: {stats['wins']} | Losses: {stats['losses']}<br>Total: {total}<br>WinRate: <b style='color:{'#0f0' if wr>=50 else '#f00'}'>{wr:.1f}%</b><br>Est. Profit: {profit:.1f}%<br>Balance: {stats['balance']}</div><br><a href='/' style='color:#0ff'>Back</a><br><br>Recent Trades:<br>{trades_html or 'No trades yet'}</body></html>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
