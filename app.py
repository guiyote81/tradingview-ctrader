from flask import Flask, request

app = Flask(__name__)


def recibir_webhook():
mensaje = request.get_data(as_text=True)

print("======================================")
print("WEBHOOK RECIBIDO")
print("Mensaje:", mensaje)
print("======================================")

return "Webhook recibido correctamente", 200


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
recibir_webhook,
methods=["POST"]
)
