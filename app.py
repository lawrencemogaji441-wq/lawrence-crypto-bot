
import os, time, threading, requests
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
# OTC pairs - using real price but labeled OTC for 24/7 trading
PAIRS=["EUR/USD (OTC)","GBP/USD (OTC)","EUR/GBP (OTC)","USD/JPY (OTC)"]
YF_MAP={"EUR/USD (OTC)":"EURUSD=X","GBP/USD (OTC)":"GBPUSD=X","EUR/GBP (OTC)":"EURGBP=X","USD/JPY (OTC)":"JPY=X"}
SCAN_INTERVAL=30  # scan every 30s for 1min signals
TRADING_START=0
TRADING_END=24  # OTC 24/7
WAT=timezone(timedelta(hours=1))

app=Flask(__name__)
last_scan="Never"; scans_count=0; signals_count=0; wins=0; losses=0; draws=0
last_signals={}; is_trading_hours=True

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:Arial;background:#0a0e1a;color:white;text-align:center;padding:30px}
.card{background:#1a2332;padding:20px;border-radius:15px;margin:15px auto;max-width:500px;border:2px solid #ff4444}
.live{color:#ff4444;font-weight:bold}</style></head>
<body><h1>LAWRENCE v6 ROLAND OTC</h1>
<div class="card"><div class="live">● v6 OTC + MARTINGALE LIVE</div>
<p>Last Scan: {{last_scan}}</p><p>Scans: {{scans}} | Signals: {{signals}}</p>
<p>✅ {{wins}} | ❌ {{losses}} | ➖ {{draws}}</p><p>WinRate: {{winrate}}% | Total: {{total}}</p><p>24/7 OTC MODE</p></div>
<div class="card">Pairs: EUR/USD OTC, GBP/USD OTC, EUR/GBP OTC, USD/JPY OTC<br>Timer: 1 min + Martingale<br>Time: 24/7 OTC</div></body></html>"""

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg},timeout=10)
    except: pass

def check_result_later(pair, entry_price, action, entry_time_str):
    def job():
        global wins,losses,draws
        time.sleep(75)  # 1m15s
        try:
            base=pair.replace(" (OTC)","")
            key=base+" (OTC)"
            df=yf.download(YF_MAP[key],period="1d",interval="1m",progress=False)
            if df.empty: return
            if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
            exit_price=float(df['Close'].iloc[-1])
            if abs(exit_price-entry_price)<0.00005:
                draws+=1
                send_telegram(f"➖ DRAW\nPair: {pair}\nEntry: {entry_price:.5f}\nExit: {exit_price:.5f}\nRefund - Use Martingale Level 1")
            elif (action in ["CALL","BUY"] and exit_price>entry_price) or (action in ["PUT","SELL"] and exit_price<entry_price):
                wins+=1
                send_telegram(f"✅ WIN!\nPair: {pair} {action}\nEntry: {entry_price:.5f}\nExit: {exit_price:.5f}\nProfit: +85%\n{entry_time_str}")
                total=wins+losses+draws; rt=wins+losses; wr=round((wins/rt*100) if rt>0 else 0,1)
                send_telegram(f"📊 STATS UPDATE\n✅ {wins} | ❌ {losses} | ➖ {draws}\nWinRate: {wr}% | Total: {total}")
            else:
                losses+=1
                # martingale hint
                send_telegram(f"❌ LOSS\nPair: {pair} {action}\nEntry: {entry_price:.5f}\nExit: {exit_price:.5f}\n➡️ Go to Martingale Level 1\n{entry_time_str}")
                total=wins+losses+draws; rt=wins+losses; wr=round((wins/rt*100) if rt>0 else 0,1)
                send_telegram(f"📊 STATS UPDATE\n✅ {wins} | ❌ {losses} | ➖ {draws}\nWinRate: {wr}% | Total: {total}")
        except Exception as e: print(e)
    threading.Thread(target=job,daemon=True).start()

def get_signal_otc(pair):
    try:
        df=yf.download(YF_MAP[pair],period="1d",interval="1m",progress=False)
        if df.empty or len(df)<30: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        close=df['Close']
        ema7=close.ewm(span=7).mean(); ema14=close.ewm(span=14).mean()
        delta=close.diff(); gain=(delta.where(delta>0,0)).rolling(14).mean(); loss=(-delta.where(delta<0,0)).rolling(14).mean()
        rsi=100-(100/(1+gain/loss))
        cp=float(close.iloc[-1]); pp=float(close.iloc[-2])
        cr=float(rsi.iloc[-1]); pr=float(rsi.iloc[-2])
        ce7=float(ema7.iloc[-1]); ce14=float(ema14.iloc[-1]); pe7=float(ema7.iloc[-2]); pe14=float(ema14.iloc[-2])
        # Fast 1m logic - EMA cross + RSI momentum
        sig=None
        # CALL when EMA7 crosses above EMA14 and RSI >50 and rising
        if pe7<=pe14 and ce7>ce14 and cr>50 and cr>pr and cr<75:
            sig="BUY"
        # Also RSI bounce from 40
        elif pr<40 and cr>=40 and cp>pp and ce7>ce14:
            sig="BUY"
        # PUT when EMA7 crosses below EMA14 and RSI <50
        elif pe7>=pe14 and ce7<ce14 and cr<50 and cr<pr and cr>25:
            sig="SELL"
        elif pr>60 and cr<=60 and cp<pp and ce7<ce14:
            sig="SELL"
        if sig:
            return {"pair":pair,"action":sig,"price":cp,"rsi":cr}
        return None
    except: return None

def bot_loop():
    global last_scan,scans_count,signals_count
    send_telegram("✅ Lawrence Sniper v6 ROLAND STYLE Started\n🔥 Features:\n• OTC Pairs 24/7 (like Roland)\n• 1 Minute Timer\n• Martingale Levels L1/L2/L3\n• Auto Result after 1 min\n• Auto Win/Loss Stats\n\nYou will get signals even at night now!")
    while True:
        try:
            now=datetime.now(WAT)
            last_scan=now.strftime("%I:%M:%S %p WAT")
            scans_count+=1
            for p in PAIRS:
                r=get_signal_otc(p)
                if r:
                    k=f"{r['pair']}_{r['action']}"
                    if k in last_signals and (time.time()-last_signals[k])<180: continue  # 3 min cooldown for 1m
                    last_signals[k]=time.time(); signals_count+=1
                    # Roland style format
                    entry_time = (now + timedelta(minutes=1)).strftime("%I:%M %p")
                    l1 = (now + timedelta(minutes=2)).strftime("%I:%M %p")
                    l2 = (now + timedelta(minutes=3)).strftime("%I:%M %p")
                    l3 = (now + timedelta(minutes=4)).strftime("%I:%M %p")
                    # First message - NEW SIGNAL
                    msg1 = f"🔔 NEW SIGNAL!\n\nTrade: {r['pair']}\n⏳ Timer: 1 minutes\n➡️ Entry: {entry_time}\n📈 Direction: {r['action']} {'🟩' if r['action']=='BUY' else '🟥'}\n\n🔄 Martingale Levels:\nLevel 1 → {l1}\nLevel 2 → {l2}\nLevel 3 → {l3}"
                    send_telegram(msg1)
                    time.sleep(2)
                    # Second message - ACTION NOW
                    msg2 = f"{'BUY' if r['action']=='BUY' else 'SELL'} {r['pair']} NOW. {'📈📈📈' if r['action']=='BUY' else '📉📉📉'}"
                    send_telegram(msg2)
                    check_result_later(r['pair'],r['price'],r['action'],last_scan)
                time.sleep(1)
            time.sleep(SCAN_INTERVAL)
        except Exception as e: print(e); time.sleep(10)

@app.route("/")
def home():
    total=wins+losses+draws; rt=wins+losses; wr=round((wins/rt*100) if rt>0 else 0,1)
    return render_template_string(HTML,last_scan=last_scan,scans=scans_count,signals=signals_count,wins=wins,losses=losses,draws=draws,winrate=wr,total=total)

threading.Thread(target=bot_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
