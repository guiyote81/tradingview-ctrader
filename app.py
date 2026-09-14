import os
import logging

from flask import Flask, request, redirect, jsonify

from ctrader_open_api import Auth


# ============================================================
# CONFIGURACIÓN
# ============================================================

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLIENT_ID = os.getenv("TRADING_CLIENT_ID")
CLIENT_SECRET = os.getenv("TRADING_CLIENT_SECRET")
REDIRECT_URI = os.getenv("TRADING_REDIRECT_URI")


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route("/")
def home():
return "Servidor TradingView -> cTrader funcionando"


# ============================================================
# LOGIN cTRADER
# ============================================================

@app.route("/login")
def login():
if not CLIENT_ID:
return "Falta TRADING_CLIENT_ID", 500

if not CLIENT_SECRET:
return "Falta TRADING_CLIENT_SECRET", 500

if not REDIRECT_URI:
return "Falta TRADING_REDIRECT_URI", 500

try:
auth = Auth(
CLIENT_ID,
CLIENT_SECRET,
REDIRECT_URI
)

auth_url = auth.getAuthUrl()

logger.info("URL de autorización generada")

return redirect(auth_url)

except Exception as e:
logger.exception("Error generando autorización")

return jsonify({
"error": str(e)
}), 500


# ============================================================
# CALLBACK cTRADER
# ============================================================

@app.route("/callback")
def callback():
code = request.args.get("code")

if not code:
error = request.args.get("error")

return jsonify({
"error": "No se recibió código de autorización",
"ctrader_error": error
}), 400

try:
auth = Auth(
CLIENT_ID,
CLIENT_SECRET,
REDIRECT_URI
)

token = auth.getToken(code)

logger.info("Autorización cTrader recibida correctamente")

return jsonify({
"ok": True,
"mensaje": "cTrader autorizado correctamente",
"token_recibido": True
})

except Exception as e:
logger.exception("Error obteniendo token")

return jsonify({
"error": str(e)
}), 500


# ============================================================
# WEBHOOK TRADINGVIEW
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():
try:
mensaje = request.get_data(as_text=True)

logger.info("======================================")
logger.info("ALERTA RECIBIDA DESDE TRADINGVIEW")
logger.info("Mensaje: %s", mensaje)
logger.info("======================================")

texto = mensaje.upper()

# ----------------------------------------------------
# Detectar instrumento
# ----------------------------------------------------

instrumento = None

if "NAS100" in texto:
instrumento = "NAS100"

elif "XAUUSD" in texto:
instrumento = "XAUUSD"

# ----------------------------------------------------
# Detectar operación
# ----------------------------------------------------

operacion = None

if "COMPRA" in texto or "BUY" in texto:
operacion = "BUY"

elif "VENTA" in texto or "SELL" in texto:
operacion = "SELL"

# ----------------------------------------------------
# Respuesta
# ----------------------------------------------------

logger.info("Instrumento detectado: %s", instrumento)
logger.info("Operación detectada: %s", operacion)

if instrumento is None:
return jsonify({
"ok": False,
"mensaje": "No se pudo detectar NAS100 o XAUUSD"
}), 200

if operacion is None:
return jsonify({
"ok": False,
"mensaje": "No se pudo detectar COMPRA o VENTA"
}), 200

# ----------------------------------------------------
# Por ahora solamente confirmamos recepción.
# La apertura de órdenes la agregamos después.
# ----------------------------------------------------

return jsonify({
"ok": True,
"instrumento": instrumento,
"operacion": operacion,
"mensaje": "Señal recibida correctamente"
}), 200

except Exception as e:
logger.exception("Error procesando webhook")

return jsonify({
"ok": False,
"error": str(e)
}), 500


# ============================================================
# ESTADO
# ============================================================

@app.route("/status")
def status():
return jsonify({
"servidor": "online",
"client_id_configurado": bool(CLIENT_ID),
"client_secret_configurado": bool(CLIENT_SECRET),
"redirect_uri_configurado": bool(REDIRECT_URI)
})


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":
app.run(
host="0.0.0.0",
port=int(os.getenv("PORT", 10000))
)
