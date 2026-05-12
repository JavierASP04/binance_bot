import requests
import time
import os
import threading
from flask import Flask

# --- CONFIGURACIÓN ---
TOKEN = "8646256822:AAH4JQgFvhE6KnLzVDOpYdF6vGjql-w4Px4"
CHAT_ID = 7873564562
TASA_OBJETIVO = 655.50
INTERVALO_MONITOR = 300

# Servidor Web Simple para que Render no nos cobre
app = Flask('')

@app.route('/')
def home():
    return "Bot de Binance está vivo!"

def run_web_server():
    # Render usa el puerto 10000 por defecto o el que asigne en la variable PORT
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- LÓGICA DEL BOT ---
ultimo_update_id = -1
ultima_revision_automatica = 0

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except: pass

def obtener_precio_p2p():
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    def consultar(tipo):
        payload = {
            "proMerchantAds": False, "page": 1, "rows": 10,
            "publisherType": "merchant", "asset": "USDT",
            "fiat": "VES", "tradeType": tipo
        }
        try:
            r = requests.post(url, json=payload, timeout=10)
            data = r.json()
            precios = [float(a['adv']['price']) for a in data['data'][:5]]
            return sum(precios) / len(precios)
        except: return None
    return consultar("SELL"), consultar("BUY")

def revisar_mensajes():
    global ultimo_update_id
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"offset": ultimo_update_id + 1, "timeout": 1}
    try:
        r = requests.get(url, params=params, timeout=5)
        for update in r.json().get("result", []):
            ultimo_update_id = update["update_id"]
            if "message" in update and "text" in update["message"]:
                if update["message"]["chat"]["id"] == CHAT_ID and update["message"]["text"] == "/price":
                    v, c = obtener_precio_p2p()
                    if v and c:
                        enviar_telegram(f"📊 *Precio:* {(v+c)/2:.2f} Bs\nV: {v:.2f} | C: {c:.2f}")
    except: pass

def monitor_loop():
    global ultima_revision_automatica
    enviar_telegram("🚀 Bot en Render (Web) Activado.")
    while True:
        revisar_mensajes()
        ahora = time.time()
        if ahora - ultima_revision_automatica >= INTERVALO_MONITOR:
            v, c = obtener_precio_p2p()
            if v and c and ((v + c) / 2) >= TASA_OBJETIVO:
                enviar_telegram(f"⚠️ *ALERTA:* {((v+c)/2):.2f} Bs")
            ultima_revision_automatica = ahora
        time.sleep(2)

if __name__ == "__main__":
    # Iniciamos el monitor en un hilo separado
    t = threading.Thread(target=monitor_loop)
    t.start()
    # Iniciamos el servidor web (lo que Render quiere ver)
    run_web_server()