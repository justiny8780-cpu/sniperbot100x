import requests
import time
import os
from telegram import Bot

# === YOUR SECRETS: Replace these ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID_HERE")
# ===================================

bot = Bot(token=TELEGRAM_TOKEN)
checked = set()

def is_elite(ca):
    try:
        # DexScreener data
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        data = requests.get(url, timeout=10).json()
        if not data.get('pairs'): return False
        pair = next((p for p in data['pairs'] if p['chainId'] == 'solana'), None)
        if not pair: return False
        
        mc = float(pair.get('fdv', 0))
        liq = float(pair.get('liquidity', {}).get('usd', 0))
        age_sec = time.time() - (pair['pairCreatedAt'] // 1000)
        buys = pair['txns']['h1']['buys']
        sells = pair['txns']['h1']['sells']
        
        # RugCheck data
        rug_url = f"https://api.rugcheck.xyz/v1/tokens/{ca}/report"
        rug = requests.get(rug_url, timeout=10).json()
        honeypot = rug.get('isHoneypot', True)
        lp_burned = rug.get('lpBurned', False)
        dev_sold = rug.get('creator', {}).get('soldPercent', 100)
        
        return (4000 <= mc <= 35000 and
                liq >= 6000 and
                lp_burned and
                not honeypot and
                dev_sold <= 15 and
                buys / max(sells, 1) >= 1.3 and
                age_sec < 7200)  # <2 hours old
    except:
        return False

while True:
    try:
        launches_url = "https://frontend-api.pump.fun/trending-pairs?limit=60&offset=0"
        launches = requests.get(launches_url).json()
        for token in launches:
            ca = token['mint']
            if ca in checked: continue
            checked.add(ca)
            
            if is_elite(ca):
                name = token['name']
                symbol = token['symbol']
                mc = token['market_cap']
                link = f"https://dexscreener.com/solana/{ca}"
                rug = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{ca}/report").json()
                dev_sold_pct = rug['creator']['soldPercent']
                msg = f"""🚀 ELITE 100K+ SNIPE ALARM

{name} (${symbol})
MC: ${mc:,.0f}
Dev sold: {dev_sold_pct}%
Link: {link}"""
                bot.send_message(chat_id=CHAT_ID, text=msg, disable_web_page_preview=True)
                print(f"🚨 PING: {name} ({ca})")
        
        time.sleep(80)  # Scan every ~1.5 min
    except Exception as e:
        print(f"Loop error: {e}")
        time.sleep(30)
