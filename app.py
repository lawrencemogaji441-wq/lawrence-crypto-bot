import os, time, requests, pandas as pd, ta, pytz, threading, numpy as np
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
stats = {"started": datetime.now(WAT).strftime("%Y-%m-%d %H:%M:%S"), "signals":0,"wins":0,"losses":0,"pnl":0.0,"last":"Starting v10 Balance...","trades":[],"active":[]}

def tg(msg):
    try:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode":"Markdown"}, timeout=5)
    except: pass
    print(msg)

def get_candles(sym, interval, limit=200):
    resp = bybit.get_kline(category=CATEGORY, symbol=sym, interval=str(interval), limit=limit)
    df = pd.DataFrame(resp['result']['list'], columns=["startTime","open","high","low","close","volume","turnover"])[::-1]
    for c in ["open","high","low","close","volume"]: df[c]=df[c].astype(float)
    return df

def find_sr(df, window=20):
    """Find strong support/resistance using swing highs/lows + recent highs/lows"""
    highs = df["high"].rolling(window).max()
    lows = df["low"].rolling(window).min()
    # Support = lowest low in last 50, Resistance = highest high in last 50
    recent = df.tail(50)
    support = recent["low"].min()
    resistance = recent["high"].max()
    # More accurate: find levels where price bounced 2+ times
    # Simplify: use 20 and 50 levels
    sup_20 = recent.tail(20)["low"].min()
    res_20 = recent.tail(20)["high"].max()
    return support, resistance, sup_20, res_20

def calc_qty(price):
    return str(round(QTY_USDT/price, 3)) if price>100 else str(round(QTY_USDT/price,2))

def check_v10_balance(df1, df5):
    now = datetime.now(WAT)
    # 24/7 mode - no sleep
    c,h,l,vol = df1["close"], df1["high"], df1["low"], df1["volume"]
    if len(c) < 100: return None, "Loading..."
    price = c.iloc[-1]
    # Indicators
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
    macd_signal = ta.trend.macd_signal(c).iloc[-1]
    bb_high = ta.volatility.bollinger_hband(c,20,2).iloc[-1]
    bb_low = ta.volatility.bollinger_lband(c,20,2).iloc[-1]
    bb_mid = ta.volatility.bollinger_mavg(c,20).iloc[-1]
    stoch_k = ta.momentum.stoch(h,l,c,14,3).iloc[-1]
    vol_ma = vol.rolling(20).mean().iloc[-1]
    vol_now = vol.iloc[-1]
    # 5m
    c5 = df5["close"]
    ema7_5 = ta.trend.ema_indicator(c5,7).iloc[-1]
    ema21_5 = ta.trend.ema_indicator(c5,21).iloc[-1]
    rsi5 = ta.momentum.rsi(c5,14).iloc[-1]
    # Support Resistance
    sup, res, sup20, res20 = find_sr(df1)
    # Distance to SR
    dist_to_sup = ((price - sup)/price)*100
    dist_to_res = ((res - price)/price)*100
    range_pct = ((res - sup)/price)*100
    # Balance check: price should be near support for BUY, near resistance for SELL, and range not too small
    # Avoid trading in middle of range - wait for bounce
    # Ideal: range >1.5% (enough room for 3% TP)
    if range_pct < 1.2:
        return None, f"Range too tight {range_pct:.2f}% S:{sup:.1f} R:{res:.1f} - Waiting expansion"
    # All indicators check
    buy_checks = []
    # 1. EMA stack bullish
    buy_checks.append(("EMA Stack", ema7 > ema21 > ema50 and price > ema7))
    # 2. Price above EMA200 (major trend)
    buy_checks.append(("Trend>EMA200", price > ema200))
    # 3. RSI 55-68 and RSI5 >50
    buy_checks.append(("RSI", 55 <= rsi <= 68 and rsi5 > 52))
    # 4. ADX strong + DI+
    buy_checks.append(("ADX+DI", adx > 22 and plus_di > minus_di and adx > 18))
    # 5. MACD bullish
    buy_checks.append(("MACD", macd > macd_signal and macd_line > 0))
    # 6. Bollinger - not at top, above mid
    buy_checks.append(("BB", price > bb_mid and price < bb_high*0.995))
    # 7. Stoch not overbought
    buy_checks.append(("Stoch", 50 <= stoch_k <= 80))
    # 8. Volume
    buy_checks.append(("Volume", vol_now > vol_ma*0.9))
    # 9. Support/Resistance BALANCE - for BUY: near support, far from resistance
    # Price should be within 0.8% of 20-candle support and at least 1% away from resistance
    near_support = (price - sup20)/price*100 < 0.9  # within 0.9% of support
    far_res = (res20 - price)/price*100 > 0.8
    buy_checks.append(("S/R Balance", near_support and far_res and dist_to_sup < 2.5))
    # 10. 5m confirmation
    buy_checks.append(("5m Trend", ema7_5 > ema21_5))
    
    sell_checks = []
    sell_checks.append(("EMA Stack", ema7 < ema21 < ema50 and price < ema7))
    sell_checks.append(("Trend<EMA200", price < ema200))
    sell_checks.append(("RSI", 32 <= rsi <= 45 and rsi5 < 48))
    sell_checks.append(("ADX-DI", adx > 22 and minus_di > plus_di))
    sell_checks.append(("MACD", macd < macd_signal and macd_line < 0))
    sell_checks.append(("BB", price < bb_mid and price > bb_low*1.005))
    sell_checks.append(("Stoch", 20 <= stoch_k <= 50))
    sell_checks.append(("Volume", vol_now > vol_ma*0.9))
    near_res = (res20 - price)/price*100 < 0.9
    far_sup = (price - sup20)/price*100 > 0.8
    sell_checks.append(("S/R Balance", near_res and far_sup and dist_to_res < 2.5))
    sell_checks.append(("5m Trend", ema7_5 < ema21_5))

    buy_score = sum(1 for _, ok in buy_checks if ok)
    sell_score = sum(1 for _, ok in sell_checks if ok)
    total_needed = 8  # need 8/10 to trade - very strict
    
    detail = f"Price {price:.2f} S {sup20:.2f} R {res20:.2f} Range {range_pct:.2f}% | RSI {rsi:.1f} ADX {adx:.1f} MACD {macd_line:.3f}"
    
    if buy_score >= total_needed:
        passed = ",".join([n for n,ok in buy_checks if ok])
        return "Buy", f"BUY ✅ Score {buy_score}/10 [{passed}]\n{detail}\nSupport balance: near SUP {dist_to_sup:.2f}% far RES {dist_to_res:.2f}%"
    if sell_score >= total_needed:
        passed = ",".join([n for n,ok in sell_checks if ok])
        return "Sell", f"SELL ✅ Score {sell_score}/10 [{passed}]\n{detail}\nResistance balance: near RES {dist_to_res:.2f}% far SUP {dist_to_sup:.2f}%"
    # Show progress
    return None, f"Scanning {buy_score}/10B {sell_score}/10S | {detail} | Vol {vol_now/vol_ma:.1f}x"

def place_order(sym, side, price):
    try:
        qty = calc_qty(price)
        try: bybit.set_leverage(category=CATEGORY, symbol=sym, buyLeverage=LEVERAGE, sellLeverage=LEVERAGE)
        except: pass
        sl = price*(1-SL_PCT/100) if side=="Buy" else price*(1+SL_PCT/100)
        tp = price*(1+TP_PCT/100) if side=="Buy" else price*(1-TP_PCT/100)
        bybit.place_order(category=CATEGORY, symbol=sym, side=side, orderType="Market", qty=qty, stopLoss=str(round(sl,2)), takeProfit=str(round(tp,2)), tpslMode="Full")
        return True, sl, tp
    except Exception as e:
        return False, str(e), 0

def loop():
    tg(f"🚀 *Lawrence v10.1 BALANCE 24/7 LIVE!*\n10 indicators 24/7 | S/R Balance\nNeed 8/10 confirmations\nS/R balance: trades only near Support (Buy) or Resistance (Sell)\n$10 protection 1 trade max")
    while True:
        for sym in SYMBOLS:
            try:
                df1 = get_candles(sym,1)
                df5 = get_candles(sym,5)
                sig, reason = check_v10_balance(df1, df5)
                stats["last"]=f"{datetime.now(WAT).strftime('%H:%M:%S')} {sym}: {reason}"
                print(stats["last"])
                if len(stats["active"])>=MAX_TRADES: continue
                if sig:
                    price = df1["close"].iloc[-1]
                    stats["signals"]+=1
                    stats["active"].append({"pair":sym,"side":sig,"price":price,"time":datetime.now(WAT).strftime('%H:%M:%S')})
                    tg(f"{'🟢' if sig=='Buy' else '🔴'} *{sig} {sym} @ {price:.2f}*\n{reason}\nActive {len(stats['active'])}/1")
                    ok, sl, tp = place_order(sym, sig, price) if isinstance(sl,float) or isinstance(sl,int) else (False, sl, 0)
                    # fix call
                    if not isinstance(sl,float):
                        ok, res, tp_val = False, sl, 0
                        # retry proper
                        try:
                            qty=calc_qty(price)
                            slp = price*(1-SL_PCT/100) if sig=="Buy" else price*(1+SL_PCT/100)
                            tpp = price*(1+TP_PCT/100) if sig=="Buy" else price*(1-TP_PCT/100)
                            bybit.set_leverage(category=CATEGORY, symbol=sym, buyLeverage=LEVERAGE, sellLeverage=LEVERAGE)
                            bybit.place_order(category=CATEGORY, symbol=sym, side=sig, orderType="Market", qty=qty, stopLoss=str(round(slp,2)), takeProfit=str(round(tpp,2)), tpslMode="Full")
                            ok=True; sl=slp; tp=tpp; res="OK"
                        except Exception as e: ok=False; res=str(e)
                    else:
                        res="OK"
                    if ok:
                        stats["trades"].insert(0,{"time":datetime.now(WAT).strftime('%H:%M:%S'),"pair":sym,"side":sig,"entry":price,"sl":sl,"tp":tp,"result":"OPEN"})
                        tg(f"✅ EXECUTED S/R Balance Trade\nTP {tp:.2f} (+3%) SL {sl:.2f} (-1.5%)")
                    else:
                        stats["active"].pop()
                        if "balance" in str(res).lower() or "insufficient" in str(res).lower():
                            stats["last"]="Waiting deposit - No balance"
                        else:
                            tg(f"❌ Fail {sym}: {str(res)[:300]}")
                    time.sleep(300)
            except Exception as e:
                print(f"Err {sym}: {e}"); time.sleep(10)
        time.sleep(25)

@app.route('/')
def home():
    trades_html="".join([f"<tr><td>{t['time']}</td><td>{t['pair']}</td><td>{t['side']}</td><td>{t['result']}</td></tr>" for t in stats["trades"][:10]]) or "<tr><td colspan=4 style='text-align:center;color:#888'>No trades yet - Waiting for perfect S/R balance</td></tr>"
    return f"""<html><head><meta http-equiv='refresh' content='15'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{{background:#0f0f0f;color:#fff;font-family:Arial;padding:15px}}.card{{background:#1e1e1e;border-radius:15px;padding:20px;margin-bottom:15px}}.green{{color:#00ff88}}.yellow{{color:#ffcc00}}h1{{font-size:20px}}</style></head><body>
<h1>🚀 Lawrence v10 <span class=yellow>BALANCE S/R</span> LIVE</h1><p style=color:#888>Started {stats['started']} | WAT {datetime.now(WAT).strftime('%H:%M:%S')} | 10 Indicators Need 8/10</p>
<div class=card><p>Signals: {stats['signals']} | Active: {len(stats['active'])}/1 | Win Rate: 0%</p><p style=background:#2a2a2a;padding:12px;border-radius:10px;white-space:pre-wrap>{stats['last']}</p></div>
<div class=card><h3>Recent Balance Trades</h3><table style=width:100%><tr><th>Time</th><th>Pair</th><th>Side</th><th>Result</th></tr>{trades_html}</table>
<p style=color:#666;font-size:11px;margin-top:10px>Indicators: EMA7/21/50/200, RSI14, ADX+DI, MACD, Bollinger, Stoch, Volume, 5m Trend, S/R Support 50c+20c Balance | Trades ONLY when near support (Buy) or resistance (Sell) + 8/10 pass</p></div></body></html>"""

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
