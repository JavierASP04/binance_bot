import requests
import time

# --- CONFIGURACIÓN ---
TOKEN = "8646256822:AAH4JQgFvhE6KnLzVDOpYdF6vGjql-w4Px4"
CHAT_ID = 7873564562  # ID numérico
TASA_OBJETIVO = 655.50
INTERVALO_MONITOR = 300  # 5 minutos para la alerta automática

# Variables de estado para el control de flujo
ultimo_update_id = -1
ultima_revision_automatica = 0

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        # Petición directa sin proxies
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def obtener_precio_p2p():
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    
    def consultar(tipo):
        payload = {
            "proMerchantAds": False, 
            "page": 1, 
            "rows": 10,
            "publisherType": "merchant", 
            "asset": "USDT",
            "fiat": "VES", 
            "tradeType": tipo
        }
        try:
            # Petición directa sin proxies
            r = requests.post(url, json=payload, timeout=10)
            data = r.json()
            # Promediamos los primeros 5 anuncios
            precios = [float(a['adv']['price']) for a in data['data'][:5]]
            return sum(precios) / len(precios)
        except Exception as e:
            print(f"Error en Binance ({tipo}): {e}")
            return None
    
    precio_venta = consultar("SELL")
    precio_compra = consultar("BUY")
    return precio_venta, precio_compra

def revisar_mensajes():
    global ultimo_update_id
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"offset": ultimo_update_id + 1, "timeout": 1}
    
    try:
        r = requests.get(url, params=params, timeout=5)
        updates = r.json().get("result", [])
        
        for update in updates:
            ultimo_update_id = update["update_id"]
            if "message" in update and "text" in update["message"]:
                texto = update["message"]["text"]
                sender_id = update["message"]["chat"]["id"]

                # Verificamos que seas tú quien escribe
                if sender_id == CHAT_ID:
                    if texto == "/price":
                        print("📝 Comando /price recibido")
                        v, c = obtener_precio_p2p()
                        if v and c:
                            prom = (v + c) / 2
                            enviar_telegram(f"📊 *Consulta Manual*\n\n*Promedio:* {prom:.2f} Bs\n*Venta:* {v:.2f}\n*Compra:* {c:.2f}")
                        else:
                            enviar_telegram("❌ No se pudo obtener el precio de Binance.")
    except Exception as e:
        print(f"Error revisando Telegram: {e}")

def monitor():
    global ultima_revision_automatica
    print(f"🚀 Monitor LOCAL iniciado.")
    print(f"🎯 Tasa objetivo: {TASA_OBJETIVO} Bs.")
    print(f"📢 Intervalo de alerta: {INTERVALO_MONITOR} segundos.")
    
    enviar_telegram("🤖 *Bot Online (Local)*\nUsa `/price` para consultar.")

    while True:
        # 1. Revisar si hay mensajes nuevos (Comandos)
        revisar_mensajes()

        # 2. Revisión automática programada
        ahora = time.time()
        if ahora - ultima_revision_automatica >= INTERVALO_MONITOR:
            v, c = obtener_precio_p2p()
            
            if v and c:
                promedio = (v + c) / 2
                print(f"[{time.strftime('%H:%M:%S')}] Check automático: {promedio:.2f} Bs")
                
                if promedio >= TASA_OBJETIVO:
                    enviar_telegram(f"⚠️ *ALERTA DE TASA*\nEl promedio P2P ha alcanzado: **{promedio:.2f} Bs**")
            
            ultima_revision_automatica = ahora
        
        # Pausa de 1 segundo para no saturar el procesador
        time.sleep(1)

if __name__ == "__main__":
    monitor()