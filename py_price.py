import requests
import time
import os
import threading
from flask import Flask

# --- CONFIGURACIÓN ---
TOKEN = "8646256822:AAH4JQgFvhE6KnLzVDOpYdF6vGjql-w4Px4"
CHAT_ID = 7873564562
TASA_OBJETIVO = 670.50
INTERVALO_MONITOR = 300

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Binance está vivo y monitoreando!"

# --- LÓGICA DEL BOT ---
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

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
        except:
            return None
    return consultar("SELL"), consultar("BUY")

def monitor_loop():
    ultimo_update_id = -1
    ultima_revision_automatica = 0
    
    print("🤖 Hilo del monitor iniciado...")
    # Pequeña espera para asegurar que el servidor web suba primero
    time.sleep(5)
    enviar_telegram("🚀 *Bot en Render Activado*\nEl monitor está corriendo en segundo plano.")
    
    while True:
        # 1. REVISAR MENSAJES (COMANDOS)
        try:
            url_upd = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {"offset": ultimo_update_id + 1, "timeout": 5}
            r = requests.get(url_upd, params=params, timeout=10)
            updates = r.json().get("result", [])
            
            for update in updates:
                ultimo_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    texto = update["message"]["text"]
                    if update["message"]["chat"]["id"] == CHAT_ID:
                        if texto == "/price":
                            v, c = obtener_precio_p2p()
                            if v and c:
                                prom = (v + c) / 2
                                enviar_telegram(f"📊 *Precio:* {prom:.2f} Bs\nV: {v:.2f} | C: {c:.2f}")
        except Exception as e:
            print(f"Error en loop de comandos: {e}")

        # 2. REVISIÓN AUTOMÁTICA
        ahora = time.time()
        if ahora - ultima_revision_automatica >= INTERVALO_MONITOR:
            try:
                v, c = obtener_precio_p2p()
                if v and c:
                    promedio = (v + c) / 2
                    if promedio >= TASA_OBJETIVO:
                        enviar_telegram(f"⚠️ *ALERTA:* {promedio:.2f} Bs")
                ultima_revision_automatica = ahora
            except:
                pass
        
        time.sleep(2)

# --- ARRANCAR MONITOR ---
# Esto se ejecuta cuando Gunicorn carga el archivo
threading.Thread(target=monitor_loop, daemon=True).start()

if __name__ == "__main__":
    # Esto solo se usa si corres el archivo manualmente
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)