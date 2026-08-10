
            
import os, time, threading, requests, json
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
PAIRS=["EUR/USD (OTC)","GBP/USD (OTC)","EUR/GBP (OTC)","USD/JPY (OTC)"]
YF_MAP={"EUR/USD (OTC)":"EURUSD=X","GBP/USD (OTC)":"GBPUSD=X","EUR/GBP (OTC)":"EURGBP=X","USD/JPY (OTC)":"JPY=X"}
WAT=timezone(timedelta(hours=1))
STATS_FILE="stats.json"

app=Flask(__name__)
last_scan="Never"; scans_count=0; signals_count=0; last_signals={}

def load_stats():
    global wins,losses,draws,signals_count,scans_count
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE,'r') as f:
                d=json.load(f)
                wins=d.get('wins',0); losses=d.get('losses',0); draws=d.get('draws',0)
                signals_count=d.get('signals_count',0); scans_count=d.get('scans_count',0)
                print(f"Loaded stats: {wins}W {losses}L {draws}D")
                return
    except: pass
    wins=0; losses=0; draws=0

def save_stats():
    try:
        with open(STATS_FILE,'w') as f:
            json.dump({'wins':wins,'losses':losses,'draws':draws,'signals_count':signals_count,'scans_count':scans_count}, f)
    except Exception as e: print(e)

load_stats()

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:Arial;background:#0a0e1a;color:white;text-align:center;padding:30px}
.card{background:#1a2332;padding:20px;border-radius:15px;margin:15px auto;max-width:500px;border:2px solid #00ff88}
.live{color:#00ff88;font-weight:bold}</style></head>
<body><h1>LAWRENCE v7 PERMANENT</h1>
<div class="card"><div class="live">● v7 SAVED FOREVER - NEVER RESETS</div>
<p>Last Scan: {{last_scan}}</p><p>Scans: {{scans}} | Signals: {{signals}}</p>
<p>✅ {{wins}} | ❌ {{losses}} | ➖ {{draws}}</p><p>WinRate: {{winrate}}% | Total: {{total}}</p><p>Saved to file ✅</p></div>
<div class="card">OTC 24/7 + Martingale + Permanent Stats</div></body></html>"""

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg},timeout=10)
    except: pass

def check_result_later(pair, entry_price, action, entry_time_str):
    def job():
        global wins,losses,draws
        time.sleep(75)
        try:
            df=yf.download(YF_MAP[pair],period="1d",interval="1m",progress=False)
            if df.empty: return
            if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
            exit_price=float(df['Close'].iloc[-1])
            if abs(exit_price-entry_price)<0.00005:
                draws+=1; save_stats()
                send_telegram(f"➖ DRAW\nPair: {pair}\nEntry: {entry_price:.5f}\nExit: {exit_price:.5f}\nRefund - Use Martingale L1")
            elif (action in ["CALL","BUY"] and exit_price>entry_price) or (action in ["PUT","SELL"] and exit_price<entry_price):
                wins+=1; save_stats()
                send_telegram(f"✅ WIN!\nPair: {pair} {action}\nEntry: {entry_price:.5f}\nExit: {exit_price:.5f}\n+85%\n{entry_time_str}")
            else:
                losses+=1; save_stats()
                send_telegram(f"❌ LOSS\nPair: {pair} {action}\nEntry: {entry_price:.5f}\nExit: {exit_price:.5f}\nGo to Martingale L1\n{entry_time_str}")
            total=wins+losses+draws; rt=wins+losses; wr=round((wins/rt*100) if rt>0 else 0,1)
            send_telegram(f"📊 STATS (SAVED)\n✅ {wins} | ❌ {losses} | ➖ {draws}\nWinRate: {wr}% | Total: {total}\nThis will NOT reset tomorrow!")
        except Exception as e: print(e)
    threading.Thread(target=job,daemon=True).start()

def get_signal(pair):
    try:
        df=yf.download(YF_MAP[pair],period="1d",interval="1m",progress=False)
        if df.empty or len(df)<30: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        close=df['Close']
        ema7=close.ewm(span=7).mean(); ema14=close.ewm(span=14).mean()
        delta=close.diff(); gain=(delta.where(delta>0,0)).rolling(14).mean(); loss=(-delta.where(delta<0,0)).rolling(14).mean()
        rsi=100-(100/(1+gain/loss))
        cp=float(close.iloc[-1]); pp=float(close.iloc[-2]); cr=float(rsi.iloc[-1]); pr=float(rsi.iloc[-2])
        ce7=float(ema7.iloc[-1]); ce14=float(ema14.iloc[-1]); pe7=float(ema7.iloc[-2]); pe14=float(ema14.iloc[-2])
        sig=None
        if pe7<=pe14 and ce7>ce14 and cr>50 and cr>pr and cr<75: sig="BUY"
        elif pr<40 and cr>=40 and cp>pp and ce7>ce14: sig="BUY"
        elif pe7>=pe14 and ce7<ce14 and cr<50 and cr<pr and cr>25: sig="SELL"
        elif pr>60 and cr<=60 and cp<pp and ce7<ce14: sig="SELL"
        if sig: return {"pair":pair,"action":sig,"price":cp,"rsi":cr}
        return None
    except: return None

def bot_loop():
    global last_scan,scans_count,signals_count
    total=wins+losses+draws; rt=wins+losses; wr=round((wins/rt*100) if rt>0 else 0,1)
    send_telegram(f"✅ Lawrence v7 PERMANENT SAVE Started\n📊 Loaded History:\n✅ {wins} | ❌ {losses} | ➖ {draws}\nWinRate: {wr}% | Total: {total}\n🔒 This will NEVER reset! Even tomorrow you will see same numbers + new trades\n24/7 OTC + Martingale")
    while True:
        try:
            now=datetime.now(WAT)
            last_scan=now.strftime("%I:%M:%S %p WAT")
            scans_count+=1
            if scans_count%20==0: save_stats()
            for p in PAIRS:
                r=get_signal(p)
                if r:
                    k=f"{r['pair']}_{r['action']}"
                    if k in last_signals and (time.time()-last_signals[k])<180: continue
                    last_signals[k]=time.time(); signals_count+=1; save_stats()
                    entry_time=(now+timedelta(minutes=1)).strftime("%I:%M %p")
                    l1=(now+timedelta(minutes=2)).strftime("%I:%M %p")
                    l2=(now+timedelta(minutes=3)).strftime("%I:%M %p")
                    l3=(now+timedelta(minutes=4)).strftime("%I:%M %p")
                    msg1=f"🔔 NEW SIGNAL!\n\nTrade: {r['pair']}\n⏳ Timer: 1 minutes\n➡️ Entry: {entry_time}\n📈 Direction: {r['action']} {'🟩' if r['action']=='BUY' else '🟥'}\n\n🔄 Martingale Levels:\nLevel 1 → {l1}\nLevel 2 → {l2}\nLevel 3 → {l3}"
                    send_telegram(msg1); time.sleep(1)
                    send_telegram(f"{'BUY' if r['action']=='BUY' else 'SELL'} {r['pair']} NOW. {'📈📈📈' if r['action']=='BUY' else '📉📉📉'}")
                    check_result_later(r['pair'],r['price'],r['action'],last_scan)
                time.sleep(1)
            time.sleep(30)
        except Exception as e: print(e); time.sleep(10)

@app.route("/")
def home():
    total=wins+losses+draws; rt=wins+losses; wr=round((wins/rt*100) if rt>0 else 0,1)
    return render_template_string(HTML,last_scan=last_scan,scans=scans_count,signals=signals_count,wins=wins,losses=losses,draws=draws,winrate=wr,total=total)

threading.Thread(target=bot_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
    
