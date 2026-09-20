from flask import Flask, request, jsonify

app = Flask(__name__)

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
lambda: jsonify({
"ok": True,
"mensaje_original": request.get_data(as_text=True),
"instrumento": (
"NAS100"
if "NAS100" in request.get_data(as_text=True).upper()
else "XAUUSD"
if "XAUUSD" in request.get_data(as_text=True).upper()
else None
),
"operacion": (
"BUY"
if (
"COMPRA" in request.get_data(as_text=True).upper()
or "BUY" in request.get_data(as_text=True).upper()
)
else "SELL"
if (
"VENTA" in request.get_data(as_text=True).upper()
or "SELL" in request.get_data(as_text=True).upper()
)
else None
)
}),
methods=["POST"]
)
