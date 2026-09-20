from flask import Flask, request
import os
import threading

from ctrader_open_api import Client, Protobuf, TcpProtocol
from ctrader_open_api.endpoints import EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
ProtoOAApplicationAuthReq,
ProtoOAApplicationAuthRes,
ProtoOAGetAccountListByAccessTokenReq,
ProtoOAGetAccountListByAccessTokenRes,
ProtoOAAccountAuthReq,
ProtoOAAccountAuthRes,
)

from twisted.internet import reactor


app = Flask(__name__)


CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

print("DEBUG: CTRADER_CLIENT_ID cargado:", bool(CLIENT_ID))
print("DEBUG: CTRADER_CLIENT_SECRET cargado:", bool(CLIENT_SECRET))
print("DEBUG: CTRADER_ACCESS_TOKEN cargado:", bool(ACCESS_TOKEN))


ctrader_client = None
account_id = None
account_authenticated = False


def conectar_ctrader():

global ctrader_client
global account_id
global account_authenticated

if not CLIENT_ID:
print("ERROR: falta CTRADER_CLIENT_ID")
return

if not CLIENT_SECRET:
print("ERROR: falta CTRADER_CLIENT_SECRET")
return

if not ACCESS_TOKEN:
print("ERROR: falta CTRADER_ACCESS_TOKEN")
return

print("================================")
print("INICIANDO CONEXION CTRADER")
print("================================")

try:

ctrader_client = Client(
EndPoints.PROTOBUF_DEMO_HOST,
EndPoints.PROTOBUF_PORT,
TcpProtocol
)

ctrader_client.setConnectedCallback(on_connected)
ctrader_client.setDisconnectedCallback(on_disconnected)
ctrader_client.setMessageReceivedCallback(on_message_received)

ctrader_client.startService()

reactor.run(installSignalHandlers=False)

except Exception as e:

print("ERROR CONECTANDO CON CTRADER:", e)


def on_connected(client):

print("================================")
print("CTRADER CONECTADO")
print("================================")

auth_request = ProtoOAApplicationAuthReq()

auth_request.clientId = CLIENT_ID
auth_request.clientSecret = CLIENT_SECRET

client.send(auth_request)


def on_disconnected(client, reason):

print("================================")
print("CTRADER DESCONECTADO")
print("Motivo:", reason)
print("================================")


def on_message_received(client, message):

global account_id
global account_authenticated

try:

payload = Protobuf.extract(message)

if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

print("CTRADER: aplicacion autenticada correctamente")

request_account = ProtoOAGetAccountListByAccessTokenReq()

request_account.accessToken = ACCESS_TOKEN

client.send(request_account)

return

if message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:

print("CTRADER: lista de cuentas recibida")

if len(payload.ctidTraderAccount) == 0:

print("ERROR: no se encontraron cuentas autorizadas")

return

account_id = payload.ctidTraderAccount[0].ctidTraderAccountId

print("CTRADER ACCOUNT ID:", account_id)

account_request = ProtoOAAccountAuthReq()

account_request.ctidTraderAccountId = account_id
account_request.accessToken = ACCESS_TOKEN

client.send(account_request)

return

if message.payloadType == ProtoOAAccountAuthRes().payloadType:

account_authenticated = True

print("================================")
print("CUENTA CTRADER AUTENTICADA")
print("ACCOUNT ID:", account_id)
print("================================")

return

except Exception as e:

print("ERROR PROCESANDO MENSAJE CTRADER:", e)


@app.route("/")
def home():

return "Servidor TradingView cTrader funcionando"


@app.route("/status")
def status():

return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():

mensaje = request.get_data(as_text=True)

print("================================")
print("WEBHOOK RECIBIDO")
print("Mensaje recibido:", mensaje)
print("================================")

return "Webhook recibido correctamente"


threading.Thread(
target=conectar_ctrader,
daemon=True
).start()
