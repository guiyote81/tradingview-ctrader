from flask import Flask, request, redirect, jsonify
import os

app = Flask(__name__)


def home():
return "Servidor TradingView -> cTrader funcionando"


def status():
return jsonify(
servidor="online",
client_id_configurado=bool(os.getenv("TRADING_CLIENT_ID")),
client_secret_configurado=bool(os.getenv("TRADING_CLIENT_SECRET")),
redirect_uri_configurado=bool(os.getenv("TRADING_REDIRECT_URI"))
)


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

return jsonify(
ok=True,
instrumento=instrumento,
operacion=operacion,
mensaje="Alerta recibida correctamente"
)


app.add_url_rule("/", "home", home)
app.add_url_rule("/status", "status", status)
app.add_url_rule("/webhook", "webhook", webhook, methods=["POST"])


if __name__ == "__main__":
app.run(
host="0.0.0.0",
port=int(os.getenv("PORT", 10000))
)
