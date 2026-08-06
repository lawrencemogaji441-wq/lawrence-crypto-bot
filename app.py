from datetime import datetime, timedelta
import pytz

def send_signal():
    try:
        eth = get_price("ETHUSDT")
        btc = get_price("BTCUSDT")
        sol = get_price("SOLUSDT")
        
        # Lagos time + 15 min expiry
        lagos = pytz.timezone("Africa/Lagos")
        now = datetime.now(lagos)
        expiry = now + timedelta(minutes=15)
        
        time_str = now.strftime("%I:%M %p")
        expiry_str = expiry.strftime("%I:%M %p")

        text = f"""⚡ LAWRENCE SNIPER - 15MIN TRADE

🟣 ETH: ${eth:.2f}
Entry: {eth:.2f} | TP: {eth*1.02:.2f} | SL: {eth*0.99:.2f}

🟠 BTC: ${btc:.2f}
Entry: {btc:.2f} | TP: {btc*1.02:.2f} | SL: {btc*0.99:.2f}

🔵 SOL: ${sol:.2f}
Entry: {sol:.2f} | TP: {sol*1.02:.2f} | SL: {sol*0.99:.2f}

⏰ Entry: {time_str} WAT
⏳ Expiry: {expiry_str} WAT (15min)
"""

        if not BOT_TOKEN or not CHAT_ID:
            return False
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False
