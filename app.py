    
import os, time, threading, requests
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
PAIRS=["EUR/USD","GBP/USD","USD/JPY"]
YF_MAP={"EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"JPY=X"}
TRADING_START=9
TRADING_END=21
WAT=timezone(timedelta(hours=1))

app=Flask(__name__)
last_scan="Never"; scans_count=0; signals_count=0; wins=0; losses=0; draws=0
last_signals={}; is_trading_hours=True
last_stats_sent_hour=-1

HTML="""<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:Arial;background:#0a0e1a;color:white;text-align:center;padding:30px}
.card{background:#1a2332;padding:20px;border-radius:15px;margin:15px auto;max-width:500px;border:2px solid #00d9ff}
.live{color:#00ff88;font-weight:bold}</style></head>
<body><h1>LAWRENCE SNIPER v5 STATS</h1>
<div class="card"><div class="live">● v5 AUTO STATS MODE</div>
<p>Last Scan: {{last_scan}}</p><p>Scans: {{scans}} | Signals: {{signals}}</p>
<p>✅ {{wins}} | ❌ {{losses}} | ➖ {{draws}}</p><p>WinRate: {{winrate}}% | Total: {{total}}</p><p>{{trading}}</p></div>
<div class="card">Auto stats sent every hour + 9PM daily report</div></body></html>"""

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg},timeout=10)
    except: pass

def send_stats_report(force=False, daily=False):
    global last_stats_sent_hour, wins, losses, draws
    now=datetime.now(WAT)
    if not daily and not force:
        if now.hour==last_stats_sent_hour: return
        if (wins+losses+draws)==0: return
    total=wins+losses+draws
    real_total=wins+losses
    winrate=round((wins/real_total*100) if real_total>0 else 0,1)
    if daily:
        msg=f"📊 DAILY REPORT {now.strftime('%b %d')}\n\n✅ Wins: {wins}\n❌ Losses: {losses}\n➖ Draws: {draws}\n📈 Total Signals: {total}\n🏆 WinRate: {winrate}% (excl. draws)\n\n{'🔥 Great day!' if winrate>=65 else '⚠️ Need improvement - v4 filtering' if total>0 else ''}\n\nBot sleeps 9PM-9AM WAT"
    else:
        msg=f"📊 STATS UPDATE {now.strftime('%I:%M %p WAT')}\n✅ {wins} | ❌ {losses} | ➖ {draws}\nWinRate: {winrate}% | Total: {total}"
    send_telegram(msg)
    last_stats_sent_hour=now.hour

def check_result_later(pair, entry_price, action, entry_time_str):
    def job():
        global wins,losses,draws
        time.sleep(330)
        try:
            df=yf.download(YF_MAP[pair],period="1d",interval="1m",progress=False)
            if df.empty: return
            if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
            exit_price=float(df['Close'].iloc[-1])
            if abs(exit_price-entry_price)<0.00005:
                draws+=1
                send_telegram(f"➖ DRAW\nPair: {pair} {action}\nEntry: {entry_price:.5f}\nExit: {exit_price:.5f}\nRefund")
            elif (action=="CALL" and exit_price>entry_price) or (action=="PUT" and exit_price<entry_price):
                wins+=1
                send_telegram(f"✅ WIN!\nPair: {pair} {action}\nEntry: {entry_price:.5f}\nExit: {exit_price:.5f}\n+85%\nTime: {entry_time_str}")
            else:
                losses+=1
                send_telegram(f"❌ LOSS\nPair: {pair} {action}\nEntry: {entry_price:.5f}\nExit: {exit_price:.5f}\n-100%\nTime: {entry_time_str}")
            # send stats after each result
            send_stats_report(force=True)
        except Exception as e: print(e)
    threading.Thread(target=job,daemon=True).start()

def get_signal(pair):
    try:
        df=yf.download(YF_MAP[pair],period="2d",interval="5m",progress=False)
        if df.empty or len(df)<60: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        close=df['Close']
        ema20=close.ewm(span=20).mean(); ema50=close.ewm(span=50).mean()
        sma20=close.rolling(20).mean(); std20=close.rolling(20).std()
        upper=sma20+2*std20; lower=sma20-2*std20; mid=sma20
        delta=close.diff(); gain=(delta.where(delta>0,0)).rolling(14).mean(); loss=(-delta.where(delta<0,0)).rolling(14).mean()
        rsi=100-(100/(1+gain/loss))
        cp=float(close.iloc[-1]); pp=float(close.iloc[-2]); cr=float(rsi.iloc[-1]); pr=float(rsi.iloc[-2])
        ce20=float(ema20.iloc[-1]); ce50=float(ema50.iloc[-1]); cm=float(mid.iloc[-1]); cu=float(upper.iloc[-1]); cl=float(lower.iloc[-1])
        up=ce20>ce50; down=ce20<ce50
        not_ob=cp<cu*0.998; not_os=cp>cl*1.002
        sig=None
        if up and pr<50 and cr>=50 and cr<62 and cp>cm and not_ob and cp>pp: sig="CALL"
        elif down and pr>50 and cr<=50 and cr>38 and cp<cm and not_os and cp<pp: sig="PUT"
        if sig: return {"pair":pair,"action":sig,"price":cp,"rsi":cr}
        return None
    except: return None

def bot_loop():
    global last_scan,scans_count,signals_count,is_trading_hours
    send_telegram("✅ Lawrence Sniper v5 Started\nFeatures:\n• Balanced 65%+ filter\n• Auto result after 5m\n• 📊 Stats after each trade\n• 📊 Hourly win/loss rate\n• 📊 Daily 9PM report")
    while True:
        try:
            now=datetime.now(WAT)
            is_trading_hours=TRADING_START<=now.hour<TRADING_END
            last_scan=now.strftime("%I:%M:%S %p WAT")
            # Hourly stats
            if now.minute==0 and now.hour!=last_stats_sent_hour and (wins+losses+draws)>0:
                send_stats_report()
            # Daily 9PM report
            if now.hour==21 and now.minute==0:
                send_stats_report(daily=True)
            if is_trading_hours:
                scans_count+=1
                for p in PAIRS:
                    r=get_signal(p)
                    if r:
                        k=f"{r['pair']}_{r['action']}"
                        if k in last_signals and (time.time()-last_signals[k])<1200: continue
                        last_signals[k]=time.time(); signals_count+=1
                        send_telegram(f"🔥 v5 BALANCED\nPair: {r['pair']}\nAction: {r['action']} {'🟢' if r['action']=='CALL' else '🔴'}\nPrice: {r['price']:.5f}\nRSI: {r['rsi']:.1f}\n5m Expiry | {last_scan}\n⏳ Result + stats in 5 mins...")
                        check_result_later(r['pair'],r['price'],r['action'],last_scan)
                    time.sleep(2)
            time.sleep(60)
        except Exception as e: print(e); time.sleep(10)

@app.route("/")
def home():
    trading="OPEN ✅" if is_trading_hours else "CLOSED (09-21 WAT)"
    total=wins+losses+draws; rt=wins+losses; wr=round((wins/rt*100) if rt>0 else 0,1)
    return render_template_string(HTML,last_scan=last_scan,scans=scans_count,signals=signals_count,wins=wins,losses=losses,draws=draws,winrate=wr,total=total,trading=trading)

threading.Thread(target=bot_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
        
