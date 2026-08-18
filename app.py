# Add this at the very bottom of Lawrence_Bybit_LIVE_AUTO_v8.py for GitHub hosting
from flask import Flask
thread_flask = Flask(__name__)

@thread_flask.route('/')
def home():
    return "Lawrence v8 SNIPER LIVE AUTO running - Bybit LIVE"

# This makes it work both as bot and website
if __name__ == "__main__":
    import threading
    threading.Thread(target=run).start()
    thread_flask.run(host='0.0.0.0', port=10000)
