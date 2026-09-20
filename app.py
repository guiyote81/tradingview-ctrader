import os
from flask import Flask, request

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
ProtoOAApplicationAuthReq,
ProtoOAGetAccountListByAccessTokenReq,
ProtoOAAccountAuthReq,
)
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOACtidTraderAccount

from twisted.internet import reactor

app = Flask(__name__)

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

client = None
account_id = None
connection_ready = False


def conectar_ctrader():
global client

if not CLIENT_ID or not CLIENT_SECRET or not ACCESS_TOKEN:
print("ERROR: Faltan credenciales de cTrader en Render.")
return

try:
client = Client(
EndPoints.PROTOBUF_DEMO_HOST,
EndPoints.PROTOBUF_PORT,
TcpProtocol
)

client.setConnectedCallback(on_connected)
client.setDisconnectedCallback(on_disconnected)
client.setMessageReceivedCallback(on_message)

client.startService()

print("Conectando con cTrader DEMO...")

except Exception as e:
print("ERROR conectando con cTrader:", e)


def on_connected(client):
print("================================")
print("CONECTADO A CTRADER DEMO")
print("================================")

auth_req = ProtoOAApplicationAuthReq()
auth_req.clientId = CLIENT_ID
auth_req.clientSecret = CLIENT_SECRET

client.send(auth_req)


def on_disconnected(client, reason):
global connection_ready
connection_ready = False
print("Desconectado de cTrader:", reason)


def on_message(client, message):
global account_id, connection_ready

try:
payload_type = message.payloadType

if payload_type == ProtoOAGetAccountListByAccessTokenReq().payloadType:
return

# Convertimos el mensaje recibido
response = Protobuf.extract(message)

print("Mensaje recibido desde cTrader:")
print(response)

# Si recibimos la lista de cuentas
if hasattr(response, "ctidTraderAccount"):
accounts = response.ctidTraderAccount

if accounts:
account_id = int(accounts[0].ctidTraderAccountId)

print("================================")
print("CUENTA CTRADER DETECTADA")
print("ctidTraderAccountId:", account_id)
print("================================")

account_auth = ProtoOAAccountAuthReq()
account_auth.ctidTraderAccountId = account_id
account_auth.accessToken = ACCESS_TOKEN

client.send(account_auth)

except Exception as e:
print("Error procesando mensaje de cTrader:", e)


def solicitar_cuentas():
if client is None:
print("cTrader todavía no está conectado.")
return

req = ProtoOAGetAccountListByAccessTokenReq()
req.accessToken = ACCESS_TOKEN

print("Solicitando cuentas autorizadas...")
client.send(req)


@app.route("/")
def home():
return "Servidor TradingView cTrader funcionando"


@app.route("/status")
def status():
return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():

mensaje = request.get_data(as_text=True).strip()

print("================================")
print("WEBHOOK RECIBIDO")
print("Mensaje recibido:", mensaje)
print("================================")

if not mensaje:
return "Mensaje vacío", 400

# POR AHORA NO EJECUTA OPERACIONES
print("PRUEBA: señal recibida correctamente.")
print("Todavía NO se ejecutará ninguna orden.")

return "Webhook recibido correctamente", 200


if __name__ == "__main__":
conectar_ctrader()

reactor.callLater(3, solicitar_cuentas)

port = int(os.environ.get("PORT", 10000))

app.run(
host="0.0.0.0",
port=port
)
