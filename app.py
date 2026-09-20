from flask import Flask, request, jsonify

app = Flask(__name__)


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
print("WEBHOOK RECIBIDO")
print("Mensaje:", mensaje)
print("Instrumento:", instrumento)
print("Operacion:", operacion)
print("======================================")

return jsonify({
"ok": True,
"instrumento": instrumento,
"operacion": operacion,
"mensaje_original": mensaje
}), 200


app.add_url_rule(
"/",
"home",
lambda: "Servidor funcionando correctamente"
)

app.add_url_rule(
"/status",
"status",
lambda: "OK"
)

app.add_url_rule(
"/webhook",
"webhook",
webhook,
methods=["POST"]
)
