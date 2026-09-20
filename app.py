import os
import threading

from flask import Flask, request

from ctrader_open_api import Client, EndPoints, TcpProtocol, Protobuf
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
ProtoOAApplicationAuthReq,
ProtoOAGetAccountListByAccessTokenReq,
ProtoOAAccountAuthReq,
ProtoOAGetAccountListByAccessTokenRes,
ProtoOAAccountAuthRes,
)

app = Flask(__name__)

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

ctrader_client = None
account_id = None
account_authenticated = False


def conectar_ctrader():
global ctrader_client

if not CLIENT_ID:
print("ERROR: falta CTRADER_CLIENT_ID")
return

if not CLIENT_SECRET:
print("ERROR: falta CTRADER_CLIENT_SECRET")
return

if not ACCESS_TOKEN:
print("ERROR: falta CTRADER_ACCESS_TOKEN")
return

try:
ctrader_client = Client(
EndPoints.PROTOBUF_DEMO_HOST,
EndPoints.PROTOBUF_PORT,
TcpProtocol
)

ctrader_client.setConnectedCallback(on_connected)
ctrader_client.setDisconnectedCallback(on_disconnected)
ctrader_client.setMessageReceivedCallback(on_message)

print("================================")
print("CONECTANDO A CTRADER DEMO...")
print("================================")

ctrader_client.startService()

except Exception as e:
print("ERROR AL CONECTAR CON CTRADER:")
print(e)


def on_connected(client):
print("================================")
print("CONEXION CON CTRADER DEMO OK")
print("================================")

auth = ProtoOAApplicationAuthReq()
auth.clientId = CLIENT_ID
auth.clientSecret = CLIENT_SECRET

client.send(auth)


def on_disconnected(client, reason):
global account_authenticated

account_authenticated = False

print("CTRADER DESCONECTADO")
print("Motivo:", reason)


def on_message(client, message):
global account_id
global account_authenticated

try:
response = Protobuf.extract(message)

print("Mensaje recibido desde cTrader:")
print(response)

if message.payloadType == ProtoOAApplicationAuthReq().payloadType:
print("Aplicacion autenticada.")

accounts_request = ProtoOAGetAccountListByAccessTokenReq()
accounts_request.accessToken = ACCESS_TOKEN

print("Solicitando cuentas autorizadas...")

client.send(accounts_request)
return

if message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:
accounts = response.ctidTraderAccount

if not accounts:
print("NO SE ENCONTRARON CUENTAS AUTORIZADAS.")
return

account_id = int(accounts[0].ctidTraderAccountId)

print("================================")
print("CUENTA ENCONTRADA")
print("ctidTraderAccountId:", account_id)
print("================================")

account_auth = ProtoOAAccountAuthReq()
account_auth.ctidTraderAccountId = account_id
account_auth.accessToken = ACCESS_TOKEN

print("Autorizando cuenta...")

client.send(account_auth)
return

if message.payloadType == ProtoOAAccountAuthRes().payloadType:
account_authenticated = True

print("================================")
print("CUENTA CTRADER AUTORIZADA")
print("================================")
print("ctidTraderAccountId:", response.ctidTraderAccountId)
print("LISTO PARA RECIBIR SEÑALES")
print("================================")

except Exception as e:
print("ERROR PROCESANDO MENSAJE CTRADER:")
print(e)


@app.route("/")
def home():
return "Servidor TradingView cTrader funcionando"


@app.route("/status")
def status():
if account_authenticated:
return "OK - cTrader conectado y cuenta autorizada"

return "OK - servidor funcionando"


@app.route("/webhook", methods=["POST"])
def webhook():
mensaje = request.get_data(as_text=True).strip()

print("================================")
print("WEBHOOK RECIBIDO")
print("Mensaje recibido:", mensaje)
print("================================")

if not mensaje:
return "Mensaje vacio", 400

mensaje = mensaje.upper()

if "COMPRA NASDAQ" in mensaje:
print("SEÑAL DETECTADA: COMPRA NASDAQ")

elif "VENTA NASDAQ" in mensaje:
print("SEÑAL DETECTADA: VENTA NASDAQ")

elif "COMPRA XAUUSD" in mensaje:
print("SEÑAL DETECTADA: COMPRA XAUUSD")

elif "VENTA XAUUSD" in mensaje:
print("SEÑAL DETECTADA: VENTA XAUUSD")

else:
print("SEÑAL NO RECONOCIDA")

print("PRUEBA: NO SE EJECUTARA NINGUNA ORDEN.")
print("================================")

return "Webhook recibido correctamente", 200


def iniciar_ctrader():
conectar_ctrader()


threading.Thread(
target=iniciar_ctrader,
daemon=True
).start()
