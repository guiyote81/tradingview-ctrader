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


print("DEBUG CLIENT ID:", bool(CLIENT_ID))
print("DEBUG CLIENT SECRET:", bool(CLIENT_SECRET))
print("DEBUG ACCESS TOKEN:", bool(ACCESS_TOKEN))


def conectar_ctrader():

if not CLIENT_ID:
print("ERROR: falta CTRADER_CLIENT_ID")
return

if not CLIENT_SECRET:
print("ERROR: falta CTRADER_CLIENT_SECRET")
return

if not ACCESS_TOKEN:
print("ERROR: falta CTRADER_ACCESS_TOKEN")
return

print("INICIANDO CONEXION CTRADER")

client = Client(
EndPoints.PROTOBUF_DEMO_HOST,
EndPoints.PROTOBUF_PORT,
TcpProtocol
)

def conectado(client):

print("CTRADER CONECTADO")

auth = ProtoOAApplicationAuthReq()

auth.clientId = CLIENT_ID
auth.clientSecret = CLIENT_SECRET

client.send(auth)


def desconectado(client, reason):

print("CTRADER DESCONECTADO")
print("Motivo:", reason)


def mensaje_recibido(client, message):

try:

payload = Protobuf.extract(message)

if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

print("CTRADER: APLICACION AUTENTICADA")

cuentas = ProtoOAGetAccountListByAccessTokenReq()

cuentas.accessToken = ACCESS_TOKEN

client.send(cuentas)

return


if message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:

print("CTRADER: LISTA DE CUENTAS RECIBIDA")

if len(payload.ctidTraderAccount) == 0:

print("ERROR: NO HAY CUENTAS AUTORIZADAS")

return

cuenta = payload.ctidTraderAccount[0]

account_id = cuenta.ctidTraderAccountId

print("CTRADER ACCOUNT ID:", account_id)

autenticar_cuenta = ProtoOAAccountAuthReq()

autenticar_cuenta.ctidTraderAccountId = account_id
autenticar_cuenta.accessToken = ACCESS_TOKEN

client.send(autenticar_cuenta)

return


if message.payloadType == ProtoOAAccountAuthRes().payloadType:

print("================================")
print("CUENTA CTRADER AUTENTICADA")
print("================================")

return


except Exception as error:

print("ERROR PROCESANDO CTRADER:", error)


client.setConnectedCallback(conectado)

client.setDisconnectedCallback(desconectado)

client.setMessageReceivedCallback(mensaje_recibido)

client.startService()

reactor.run(installSignalHandlers=False)


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
