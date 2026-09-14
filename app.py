from flask import Flask, request, jsonify
import os

app = Flask(__name__)

CLIENT_ID = os.getenv("TRADING_CLIENT_ID")
CLIENT_SECRET = os.getenv("TRADING_CLIENT_SECRET")
REDIRECT_URI = os.getenv("TRADING_REDIRECT_URI")


@app.route("/")
def home():
return "Servidor TradingView -> cTrader funcionando"


@app.route("/status")
def status():
return jsonify({
"servidor": "online",
"client_id_configurado": bool(CLIENT_ID),
"client_secret_configurado": bool(CLIENT_SECRET),
"redirect_uri_configurado": bool(REDIRECT_URI)
})


@app.route("/webhook", methods=["POST"])
def webhook():
mensaje = request.get_data(as_text=True)
texto = mensaje.upper()

instrumento = None
operacion = None

if "NAS100" in texto:
instrumento = "NAS100"
elif "XAUUSD" in texto:
instrumento = "XAUUSD"

if "COMPRA" in texto or "BUY" in texto:
operacion = "BUY"
elif "VENTA" in texto or "SELL" in texto:
operacion = "SELL"

print("======================================")
print("ALERTA RECIBIDA DESDE TRADINGVIEW")
print("Mensaje:", mensaje)
print("Instrumento:", instrumento)
print("Operacion:", operacion)
print("======================================")

return jsonify({
"ok": True,
"instrumento": instrumento,
"operacion": operacion,
"mensaje": "Alerta recibida correctamente"
}), 200


if __name__ == "__main__":
app.run(
host="0.0.0.0",
port=int(os.getenv("PORT", 10000))
)
