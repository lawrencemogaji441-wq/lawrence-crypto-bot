import os, time, requests, pandas as pd, ta, pytz, threading
from datetime import datetime
from pybit.unified_trading import HTTP
from flask import Flask

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
CATEGORY = "linear"
QTY_USDT = 10
LEVERAGE = "10"
SL_PCT = 1.5
TP_PCT = 3.0
MAX_TRADES = 1
WAT = pytz.timezone("Africa/Lagos")

bybit = HTTP(testnet=False, api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET) if BYBIT_API_KEY else None
app = Flask(__name__)
stats = {"started": datetime.now(WAT).strftime("%Y-%m-%d %H:%M:%S"), "signals":0,"wins":0,"losses":0,"pnl":0.0,"last":"Starting v10.2 24/7...","trades":[],"active":[]}

def tg(msg):
    try:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode":"Markdown"}, timeout=5)
    except: pass
    print(msg)

def get_candles(sym, interval, limit=200):
    if not bybit:
        raise Exception("Keys not set")
    resp = bybit.get_kline(category=CATEGORY, symbol=sym, interval=str(interval), limit=limit)
    df = pd.DataFrame(resp['result']['list'], columns=["startTime","open","high","low","close","volume","turnover"])[::-1]
    for c in ["open","high","low","close","volume"]: df[c]=df[c].astype(float)
    return df

def find_sr(df):
    recent = df.tail(50)
    support = recent["low"].min()
    resistance = recent["high"].max()
    sup20 = recent.tail(20)["low"].min()
    res20 = recent.tail(20)["high"].max()
    return support, resistance, sup20, res20

def calc_qty(price):
    return str(round(QTY_USDT/price, 3)) if price>100 else str(round(QTY_USDT/price,2))

def check_v10(sym, df1, df5):
    c,h,l,vol = df1["close"], df1["high"], df1["low"], df1["volume"]
    if len(c) < 100: return None, "Loading..."
    price = c.iloc[-1]
    ema7 = ta.trend.ema_indicator(c,7).iloc[-1]
    ema21 = ta.trend.ema_indicator(c,21).iloc[-1]
    ema50 = ta.trend.ema_indicator(c,50).iloc[-1]
    ema200 = ta.trend.ema_indicator(c,200).iloc[-1] if len(c)>=200 else ema50
    rsi = ta.momentum.rsi(c,14).iloc[-1]
    adx = ta.trend.adx(h,l,c,14).iloc[-1]
    plus_di = ta.trend.adx_pos(h,l,c,14).iloc[-1]
    minus_di = ta.trend.adx_neg(h,l,c,14).iloc[-1]
    macd_line = ta.trend.macd_diff(c).iloc[-1]
    macd = ta.trend.macd(c).iloc[-1]
    macd_sig = ta.trend.macd_signal(c).iloc[-1]
    bb_high = ta.volatility.bollinger_hband(c,20,2).iloc[-1]
    bb_low = ta.volatility.bollinger_lband(c,20,2).iloc[-1]
    bb_mid = ta.volatility.bollinger_mavg(c,20).iloc[-1]
    stoch_k = ta.momentum.stoch(h,l,c,14,3).iloc[-1]
    vol_ma = vol.rolling(20).mean().iloc[-1]
    vol_now = vol.iloc[-1]
    c5 = df5["close"]
    ema7_5 = ta.trend.ema_indicator(c5,7).iloc[-1]
    ema21_5 = ta.trend.ema_indicator(c5,21).iloc[-1]
    rsi5 = ta.momentum.rsi(c5,14).iloc[-1]
    sup, res, sup20, res20 = find_sr(df1)
    dist_sup = ((price - sup)/price)*100
    dist_res = ((res - price)/price)*100
    range_pct = ((res - sup)/price)*100
    if range_pct < 1.2:
        return None, f"Range tight {range_pct:.2f}% S:{sup:.1f} R:{res:.1f} - Waiting"
    # BUY checks
    b1 = ema7 > ema21 > ema50 and price > ema7
    b2 = price > ema200
    b3 = 55 <= rsi <= 68 and rsi5 > 52
    b4 = adx > 22 and plus_di > minus_di
    b5 = macd > macd_sig and macd_line > 0
    b6 = price > bb_mid and price < bb_high*0.995
    b7 = 50 <= stoch_k <= 80
    b8 = vol_now > vol_ma*0.9
    b9 = ((price - sup20)/price*100 < 0.9) and ((res20 - price)/price*100 > 0.8) and dist_sup < 2.5
    b10 = ema7_5 > ema21_5
    buy_score = sum([b1,b2,b3,b4,b5,b6,b7,b8,b9,b10])
    s1 = ema7 < ema21 < ema50 and price < ema7
    s2 = price < ema200
    s3 = 32 <= rsi <= 45 and rsi5 < 48
    s4 = adx > 22 and minus_di > plus_di
    s5 = macd < macd_sig and macd_line < 0
    s6 = price < bb_mid and price > bb_low*1.005
    s7 = 20 <= stoch_k <= 50
    s8 = vol_now > vol_ma*0.9
    s9 = ((res20 - price)/price*100 < 0.9) and ((price - sup20)/price*100 > 0.8) and dist_res < 2.5
    s10 = ema7_5 < ema21_5
    sell_score = sum([s1,s2,s3,s4,s5,s6,s7,s8,s9,s10])
    detail = f"P:{price:.2f} S20:{sup20:.1f} R20:{res20:.1f} Range:{range_pct:.1f}% RSI:{rsi:.0f} ADX:{adx:.0f}"
    if buy_score >= 8:
        return "Buy", f"BUY Score {buy_score}/10 {detail} Near SUP {dist_sup:.2f}%"
    if sell_score >= 8:
        return "Sell", f"SELL Score {sell_score}/10 {detail} Near RES {dist_res:.2f}%"
    return None, f"Scan {buy_score}B/{sell_score}S | {detail} | Vol {vol_now/vol_ma:.1f}x"

def place_order(sym, side, price):
    qty = calc_qty(price)
    try: bybit.set_leverage(category=CATEGORY, symbol=sym, buyLeverage=LEVERAGE, sellLeverage=LEVERAGE)
    except: pass
    sl = price*(1-SL_PCT/100) if side=="Buy" else price*(1+SL_PCT/100)
    tp = price*(1+TP_PCT/100) if side=="Buy" else price*(1-TP_PCT/100)
    bybit.place_order(category=CATEGORY, symbol=sym, side=side, orderType="Market", qty=qty, stopLoss=str(round(sl,2)), takeProfit=str(round(tp,2)), tpslMode="Full")
    return sl, tp

def loop():
    tg("🚀 *Lawrence v10.2 BALANCE 24/7 LIVE!*\n10 indicators 8/10 needed\nS/R Balance: near SUP=Buy near RES=Sell\n24/7 NO SLEEP + $10 protection 1 trade max\nDashboard: https://lawrence-crypto-bot.onrender.com")
    while True:
        for sym in SYMBOLS:
            try:
                df1 = get_candles(sym,1)
                df5 = get_candles(sym,5)
                sig, reason = check_v10(sym, df1, df5)
                stats["last"]=f"{datetime.now(WAT).strftime('%H:%M:%S')} {sym}: {reason}"
                print(stats["last"])
                if len(stats["active"])>=MAX_TRADES: continue
                if sig:
                    price = df1["close"].iloc[-1]
                    stats["signals"]+=1
                    stats["active"].append({"pair":sym,"side":sig,"price":price,"time":datetime.now(WAT).strftime('%H:%M:%S')})
                    tg(f"{'🟢' if sig=='Buy' else '🔴'} *{sig} {sym} @ {price:.2f}*\n{reason}\nActive {len(stats['active'])}/1")
                    try:
                        sl,tp = place_order(sym, sig, price)
                        stats["trades"].insert(0,{"time":datetime.now(WAT).strftime('%H:%M:%S'),"pair":sym,"side":sig,"entry":price,"sl":sl,"tp":tp,"result":"OPEN"})
                        tg(f"✅ EXECUTED TP {tp:.2f} SL {sl:.2f}")
                    except Exception as e:
                        err=str(e)
                        stats["active"].pop()
                        if "balance" in err.lower() or "insufficient" in err.lower():
                            stats["last"]="Waiting deposit - Add $12 to UTA"
                        else:
                            tg(f"❌ Fail {sym}: {err[:300]}")
                    time.sleep(300)
            except Exception as e:
                print(f"Err {sym}: {e}"); time.sleep(10)
        time.sleep(25)

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/')
def home():
    trades_html="".join([f"<tr><td>{t['time']}</td><td>{t['pair']}</td><td>{t['side']}</td><td>{t['result']}</td></tr>" for t in stats["trades"][:10]]) or "<tr><td colspan=4 style='text-align:center;color:#888'>No trades yet - Waiting for perfect S/R balance (24/7 scanning)</td></tr>"
    return f"""<html><head><meta http-equiv='refresh' content='15'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{{background:#0f0f0f;color:#fff;font-family:Arial;padding:15px}}.card{{background:#1e1e1e;border-radius:15px;padding:20px;margin-bottom:15px}}.green{{color:#00ff88}}.yellow{{color:#ffcc00}}h1{{font-size:20px}}</style></head><body>
<h1>🚀 Lawrence v10.1 <span class=yellow>BALANCE 24/7</span> LIVE</h1><p style=color:#888>Started {stats['started']} | WAT {datetime.now(WAT).strftime('%H:%M:%S')} | Need 8/10 | 24/7 NO SLEEP</p>
<div class=card><p>Signals: {stats['signals']} | Active: {len(stats['active'])}/1 | Win Rate: 0%</p><p style=background:#2a2a2a;padding:12px;border-radius:10px;white-space:pre-wrap>{stats['last']}</p></div>
<div class=card><h3>Recent Balance Trades</h3><table style=width:100%><tr><th>Time</th><th>Pair</th><th>Side</th><th>Result</th></tr>{trades_html}</table>
<p style=color:#666;font-size:11px;margin-top:10px>10 Indicators: EMA7/21/50/200 RSI ADX+DI MACD BB Stoch Volume 5m S/R | S/R Balance + 8/10 pass | 24/7 scanning</p></div></body></html>"""

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
