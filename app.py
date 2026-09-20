from flask import Flask, request

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
lambda: (
print("================================"),
print("WEBHOOK RECIBIDO"),
print("Mensaje recibido:", request.get_data(as_text=True)),
print("================================"),
"Webhook recibido correctamente"
)[-1],
methods=["POST"]
)
