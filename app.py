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


# ============================================================
# VARIABLES DE RENDER
# ============================================================

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

print("DEBUG: CTRADER_CLIENT_ID cargado:", bool(CLIENT_ID))
print("DEBUG: CTRADER_CLIENT_SECRET cargado:", bool(CLIENT_SECRET))
print("DEBUG: CTRADER_ACCESS_TOKEN cargado:", bool(ACCESS_TOKEN))


# ============================================================
# VARIABLES CTRADER
# ============================================================

ctrader_client = None
account_id = None
account_authenticated = False


# ============================================================
# CONEXIÓN CON CTRADER
# ============================================================

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


# ============================================================
# CUANDO CONECTA
# ============================================================

def on_connected(client):
print("================================")
print("CTRADER CONECTADO")
print("================================")

request = ProtoOAApplicationAuthReq()
request.clientId = CLIENT_ID
request.clientSecret = CLIENT_SECRET

client.send(request)


# ============================================================
# CUANDO SE DESCONECTA
# ============================================================

def on_disconnected(client, reason):
print("================================")
print("CTRADER DESCONECTADO")
print("Motivo:", reason)
print("================================")


# ============================================================
# MENSAJES CTRADER
# ============================================================

def on_message_received(client, message):
global account_id
global account_authenticated

try:
payload = Protobuf.extract(message)

# --------------------------------------------
# AUTENTICACION DE LA APLICACION
# --------------------------------------------

if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

print("CTRADER: aplicacion autenticada correctamente")

request = ProtoOAGetAccountListByAccessTokenReq()
request.accessToken = ACCESS_TOKEN

client.send(request)

return

# --------------------------------------------
# LISTA DE CUENTAS
# --------------------------------------------

if message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:

print("CTRADER: lista de cuentas recibida")

if len(payload.ctidTraderAccount) == 0:
print("ERROR: no se encontraron cuentas autorizadas")
return

# Tomamos la primera cuenta autorizada.
account_id = payload.ctidTraderAccount[0].ctidTraderAccountId

print("CTRADER ACCOUNT ID:", account_id)

request = ProtoOAAccountAuthReq()
request.ctidTraderAccountId = account_id
request.accessToken = ACCESS_TOKEN

client.send(request)

return

# --------------------------------------------
# CUENTA AUTENTICADA
# --------------------------------------------

if message.payloadType == ProtoOAAccountAuthRes().payloadType:

account_authenticated = True

print("================================")
print("CUENTA CTRADER AUTENTICADA")
print("ACCOUNT ID:", account_id)
print("================================")

return

except Exception as e:
print("ERROR PROCESANDO MENSAJE CTRADER:", e)


# ============================================================
# WEB
# ============================================================

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


# ============================================================
# INICIAR CTRADER EN SEGUNDO PLANO
# ============================================================

threading.Thread(
target=conectar_ctrader,
daemon=True
).start()
