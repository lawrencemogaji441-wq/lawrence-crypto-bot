import os, requests
from flask import Flask, request
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send(t, chat=CHAT_ID):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":chat,"text":t}, timeout=10)
    except: pass

@app.route("/")
def home(): return "Lawrence SMART BOT - Auto + Reply LIVE!"

@app.route("/price")
def price():
    try:
        r=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",timeout=10).json()
        eth=float(r['ethereum']['usd'])
    except: eth=3800.0
    
    lagos = pytz.timezone('Africa/Lagos')
    now = datetime.now(lagos)
    
    if (now.hour + now.minute) % 2 == 0:
        direction="BUY 🟢"; action="LONG"; tp=eth*1.02; sl=eth*0.99
    else:
        direction="SELL 🔴"; action="SHORT"; tp=eth*0.98; sl=eth*1.01

    t1 = now.strftime("%I:%M %p")
    t2 = (now + timedelta(minutes=1)).strftime("%I:%M %p")
    t3 = (now + timedelta(minutes=2)).strftime("%I:%M %p")

    msg=f"""📡 Lawrence Signal - {action}
⏰ Lagos: {t1}
Trade: ETH/USD
Direction: {direction}
Price: ${eth:.2f}
TP: ${tp:.2f} | SL: ${sl:.2f}
5x Isolated
Martingale: {t1}, {t2}, {t3}"""
    send(msg)
    return msg.replace("\n","<br>")

# NEW - This makes bot reply when you message it!
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        msg = data["message"]["text"]
        cid = data["message"]["chat"]["id"]
        
        if "/start" in msg:
            reply = "Hello Lawrence! 🤖\nBot is LIVE!\n\nCommands:\n/price - Get price now\n/status - Bot status"
        elif "/price" in msg:
            reply = price()
            return "ok"
        elif "/status" in msg:
            reply = "✅ Auto signals: Every 15min\n✅ Lagos Time Fixed\n✅ BUY & SELL Working!"
        else:
            reply = f"You said: {msg}\nBot is working! Type /price"

        send(reply, cid)
    except: pass
    return "ok"

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
