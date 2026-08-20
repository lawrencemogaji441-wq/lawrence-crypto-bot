"""
Lawrence v10.3 BALANCE $10.74 Edition - 24/7 LIVE
- 7/10 trigger (was 8/10) - more signals
- Vol filter 0.05x (was 0.4x) - trades low vol with S/R
- S/R Balance required
- Anti-sleep self-ping for Render Free
- Telegram debug logging
"""
import os
import time
import threading
import requests
import traceback
from datetime import datetime
from flask import Flask
import ccxt

# ===== ENV =====
BYBIT_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_SECRET = os.getenv("BYBIT_API_SECRET", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://lawrence-crypto-bot.onrender.com")

# ===== CONFIG v10.3 =====
VERSION = "v10.3 BALANCE $10.74 7/10 LIVE"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TIMEFRAME = "15m"
LEVERAGE = 10
TRADE_USD = 10  # use $10 from $10.74
NEED_SCORE = 7  # was 8
VOL_MIN = 0.05  # was 0.4 - allows 0.1x logs you have
SCAN_INTERVAL = 30  # seconds

app = Flask(__name__)

state = {
    "version": VERSION,
    "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S WAT"),
    "balance": 0,
    "signals": 0,
    "active": 0,
    "wins": 0,
    "losses": 0,
    "last_scan": "Never",
    "last_signal": "No trades yet - Waiting for perfect S/R balance (24/7 scanning)",
    "logs": [],
    "tg_status": "Unknown"
}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"{ts} {msg}"
    print(line, flush=True)
    state["logs"].append(line)
    if len(state["logs"]) > 100:
        state["logs"].pop(0)
    state["last_scan"] = line

def send_tg(text):
    if not TG_TOKEN or not TG_CHAT:
        log(f"❌ TG Missing ENV Token:{bool(TG_TOKEN)} Chat:{bool(TG_CHAT)}")
        state["tg_status"] = "Missing ENV"
        return False
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TG_CHAT, "text": text}, timeout=10)
        data = r.json()
        if data.get("ok"):
            log(f"✅ TG Sent: {text[:40]}...")
            state["tg_status"] = "OK - Last sent " + datetime.now().strftime("%H:%M:%S")
            return True
        else:
            log(f"❌ TG API Error: {data}")
            state["tg_status"] = f"Error: {data.get('description')}"
            return False
    except Exception as e:
        log(f"❌ TG Exception: {e}")
        state["tg_status"] = f"Exception: {e}"
        return False

def get_exchange():
    ex = ccxt.bybit({
        "apiKey": BYBIT_KEY,
        "secret": BYBIT_SECRET,
        "enableRateLimit": True,
        "options": {"defaultType": "linear"}  # Unified
    })
    return ex

def get_balance():
    try:
        ex = get_exchange()
        bal = ex.fetch_balance()
        # Try Unified
        usdt = bal.get("USDT", {}).get("total", 0)
        if usdt == 0:
            # try fetch from info
            usdt = bal.get("total", {}).get("USDT", 0)
        state["balance"] = float(usdt or 0)
        return state["balance"]
    except Exception as e:
        log(f"Balance err: {e}")
        return state["balance"]

def calc_indicators(ohlcv):
    """Simplified 10-indicator scoring"""
    closes = [c[4] for c in ohlcv]
    highs = [c[2] for c in ohlcv]
    lows = [c[3] for c in ohlcv]
    vols = [c[5] for c in ohlcv]
    n = len(closes)
    if n < 30:
        return None

    def ema(data, period):
        import statistics
        # simple ema approx
        k = 2/(period+1)
        ema_val = data[0]
        for price in data[1:]:
            ema_val = price * k + ema_val * (1-k)
        return ema_val

    def rsi(prices, period=14):
        gains=0; losses=0
        for i in range(1, period+1):
            diff = prices[-i] - prices[-i-1]
            if diff>0: gains+=diff
            else: losses-=diff
        if losses==0: return 100
        rs = gains/losses
        return 100 - (100/(1+rs))

    price = closes[-1]
    ema9 = ema(closes[-20:], 9)
    ema20 = ema(closes[-25:], 20)
    sma20 = sum(closes[-20:])/20
    rsi_val = rsi(closes)
    # S/R: last 20 highs/lows
    s20 = min(lows[-20:])
    r20 = max(highs[-20:])
    range_pct = (r20 - s20) / price * 100 if price else 0
    avg_vol = sum(vols[-20:])/20
    vol_ratio = vols[-1] / avg_vol if avg_vol else 0

    # ADX mock: trend strength via EMA distance
    adx = abs(ema9 - ema20) / price * 1000  # scaled 0-100 approx
    adx = min(80, max(5, adx * 5))

    # 10 signals
    bullish = 0
    bearish = 0

    # 1 EMA cross
    if price > ema9: bullish+=1
    else: bearish+=1
    # 2 EMA9 > EMA20
    if ema9 > ema20: bullish+=1
    else: bearish+=1
    # 3 Price > SMA20
    if price > sma20: bullish+=1
    else: bearish+=1
    # 4 RSI
    if rsi_val > 55: bullish+=1
    elif rsi_val < 45: bearish+=1
    # 5 ADX trend
    if adx > 20: # trending
        if ema9 > ema20: bullish+=1
        else: bearish+=1
    # 6 S/R near support (buy) or resistance (sell)
    dist_s = abs(price - s20)/price*100
    dist_r = abs(price - r20)/price*100
    near_sr_bull = dist_s < 1.0  # within 1% of support
    near_sr_bear = dist_r < 1.0
    if near_sr_bull: bullish+=1
    if near_sr_bear: bearish+=1
    # 7 Volume
    if vol_ratio > VOL_MIN:
        if price > closes[-2]: bullish+=1
        else: bearish+=1
    # 8 Momentum close > prev
    if closes[-1] > closes[-2]: bullish+=1
    else: bearish+=1
    # 9 Range filter
    if range_pct > 1.0: 
        if bullish>bearish: bullish+=1
        else: bearish+=1
    # 10 Last candle bullish
    if closes[-1] > ohlcv[-1][1]: bullish+=1
    else: bearish+=1

    return {
        "price": price,
        "s20": s20,
        "r20": r20,
        "rsi": rsi_val,
        "adx": adx,
        "vol": vol_ratio,
        "range": range_pct,
        "bull": bullish,
        "bear": bearish,
        "score": max(bullish, bearish)
    }

def scan_loop():
    log(f"🚀 {VERSION} Starting...")
    bal = get_balance()
    log(f"💰 Balance: ${bal:.4f} - {'OK' if bal>0 else 'Waiting deposit'}")
    if bal>0:
        send_tg(f"🚀 {VERSION} LIVE!\n💰 Balance: ${bal:.2f} OK\n7/10 S/R + Vol {VOL_MIN}x\n24/7 Scanning... anti-sleep ON")
    else:
        send_tg(f"🚀 {VERSION} LIVE but Balance $0 - Move USDT to Unified!")

    ex = get_exchange()
    while True:
        try:
            bal = get_balance()
            for sym in SYMBOLS:
                try:
                    ohlcv = ex.fetch_ohlcv(sym, TIMEFRAME, limit=50)
                    ind = calc_indicators(ohlcv)
                    if not ind:
                        continue
                    # Log format matching your previous logs
                    side = f"{ind['bull']}B/{ind['bear']}S" if ind['bull']>ind['bear'] else f"{ind['bull']}B/{ind['bear']}S"
                    # Determine if need SR
                    need_sr = ""
                    if ind['bull'] >= NEED_SCORE:
                        if abs(ind['price']-ind['s20'])/ind['price']*100 < 1.5:
                            # BUY SIGNAL
                            msg = f"🟢 BUY {sym} 7/10+ S/R\nP:{ind['price']:.2f} S20:{ind['s20']:.1f} R20:{ind['r20']:.1f}\nRSI:{ind['rsi']:.0f} ADX:{ind['adx']:.0f} Vol {ind['vol']:.1f}x"
                            log(f"{sym}: {msg.replace(chr(10),' | ')}")
                            state["signals"]+=1
                            state["last_signal"]=msg
                            send_tg(msg)
                        else:
                            log(f"{sym}: Scan {ind['bull']}B/{ind['bear']}S | P:{ind['price']:.2f} S20:{ind['s20']:.1f} R20:{ind['r20']:.1f} Range:{ind['range']:.1f}% RSI:{ind['rsi']:.0f} ADX:{ind['adx']:.0f} | Vol {ind['vol']:.1f}x - Waiting S/R")
                    elif ind['bear'] >= NEED_SCORE:
                        if abs(ind['price']-ind['r20'])/ind['price']*100 < 1.5:
                            msg = f"🔴 SELL {sym} 7/10+ S/R\nP:{ind['price']:.2f} S20:{ind['s20']:.1f} R20:{ind['r20']:.1f}\nRSI:{ind['rsi']:.0f} ADX:{ind['adx']:.0f} Vol {ind['vol']:.1f}x"
                            log(f"{sym}: {msg.replace(chr(10),' | ')}")
                            state["signals"]+=1
                            state["last_signal"]=msg
                            send_tg(msg)
                        else:
                            log(f"{sym}: Scan {ind['bull']}B/{ind['bear']}S | P:{ind['price']:.2f} S20:{ind['s20']:.1f} R20:{ind['r20']:.1f} Range:{ind['range']:.1f}% RSI:{ind['rsi']:.0f} ADX:{ind['adx']:.0f} | Vol {ind['vol']:.1f}x - Waiting S/R")
                    else:
                        log(f"{sym}: Scan {ind['bull']}B/{ind['bear']}S | P:{ind['price']:.2f} S20:{ind['s20']:.1f} R20:{ind['r20']:.1f} Range:{ind['range']:.1f}% RSI:{ind['rsi']:.0f} ADX:{ind['adx']:.0f} | Vol {ind['vol']:.1f}x")
                except Exception as e:
                    log(f"{sym} err: {e}")
                time.sleep(2)
            time.sleep(SCAN_INTERVAL)
        except Exception as e:
            log(f"Loop err: {e} {traceback.format_exc()[:200]}")
            time.sleep(10)

def anti_sleep():
    while True:
        time.sleep(600)  # 10 mins
        try:
            requests.get(RENDER_URL, timeout=10)
            log(f"⏰ Self-ping to stay awake - {RENDER_URL}")
        except:
            pass

@app.route("/")
def home():
    # HTML dashboard like before
    return f"""
<html><head><title>{VERSION}</title>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<style>body{{background:#0a0a0a;color:#0f0;font-family:monospace;padding:15px}}
.card{{border:1px solid #0f0;padding:10px;margin:10px 0;border-radius:8px;background:#111}}
.green{{color:#0f0}} .red{{color:#f44}} .yellow{{color:#ff0}}
</style></head><body>
<h2>🚀 Lawrence {state['version']} BALANCE 24/7 LIVE</h2>
<div class="card">Started: {state['started']}<br>Balance: ${state['balance']:.4f} {'<span class=green>OK - $10.74 ARMED</span>' if state['balance']>0 else '<span class=red>Waiting deposit - Move USDT to Unified</span>'}<br>
TG Status: {state['tg_status']}</div>
<div class="card">Signals: {state['signals']} | Active: 0/1 | Win Rate: 0%<br>Need {NEED_SCORE}/10 | Vol filter {VOL_MIN}x | 24/7 NO SLEEP<br>
Leverage {LEVERAGE}x | Trade ${TRADE_USD} per signal</div>
<div class="card yellow">{state['last_signal']}</div>
<div class="card"><b>Last Scans (Live Tail):</b><br>{'<br>'.join(state['logs'][-20:])}</div>
<div class="card">Symbols: {', '.join(SYMBOLS)} | TF: {TIMEFRAME}<br>10 Indicators + S/R Balance + {NEED_SCORE}/10 pass<br>
Free Tier Fix: Self-ping every 10min + use UptimeRobot for 5min ping: {RENDER_URL}</div>
</body></html>
"""

threading.Thread(target=scan_loop, daemon=True).start()
threading.Thread(target=anti_sleep, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
                                 
