from flask import Flask, request
import os
import threading

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from twisted.internet import reactor

app = Flask(__name__)

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")


def iniciar_ctrader():
print("================================")
print("INICIANDO CTRADER")
print("================================")

if not CLIENT_ID:
print("ERROR: falta CTRADER_CLIENT_ID")
return

if not CLIENT_SECRET:
print("ERROR: falta CTRADER_CLIENT_SECRET")
return

if not ACCESS_TOKEN:
print("ERROR: falta CTRADER_ACCESS_TOKEN")
return

client = Client(
EndPoints.PROTOBUF_DEMO_HOST,
EndPoints.PROTOBUF_PORT,
TcpProtocol
)

def conectado(client):
print("CTRADER: CONECTADO")

auth = ProtoOAApplicationAuthReq()
auth.clientId = CLIENT_ID
auth.clientSecret = CLIENT_SECRET

client.send(auth)

def desconectado(client, reason):
print("CTRADER: DESCONECTADO")
print("Motivo:", reason)

def mensaje_recibido(client, message):
if message.payloadType == ProtoOAApplicationAuthRes().payloadType:
print("CTRADER: APLICACION AUTENTICADA")

cuentas = ProtoOAGetAccountListByAccessTokenReq()
cuentas.accessToken = ACCESS_TOKEN

client.send(cuentas)

elif message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:
respuesta = Protobuf.extract(message)

print("CTRADER: LISTA DE CUENTAS RECIBIDA")

if len(respuesta.ctidTraderAccount) == 0:
print("ERROR: NO HAY CUENTAS AUTORIZADAS")
return

cuenta = respuesta.ctidTraderAccount[0]
account_id = cuenta.ctidTraderAccountId

print("CTRADER ACCOUNT ID:", account_id)

auth_cuenta = ProtoOAAccountAuthReq()
auth_cuenta.ctidTraderAccountId = account_id
auth_cuenta.accessToken = ACCESS_TOKEN

client.send(auth_cuenta)

elif message.payloadType == ProtoOAAccountAuthRes().payloadType:
respuesta = Protobuf.extract(message)

print("================================")
print("CUENTA CTRADER AUTENTICADA")
print("ACCOUNT ID:", respuesta.ctidTraderAccountId)
print("================================")

else:
print("CTRADER MENSAJE:", Protobuf.extract(message))

client.setConnectedCallback(conectado)
client.setDisconnectedCallback(desconectado)
client.setMessageReceivedCallback(mensaje_recibido)

client.startService()
reactor.run(installSignalHandlers=False)


@app.add_url_rule(
"/",
"home",
lambda: "Servidor funcionando correctamente"
)

@app.add_url_rule(
"/status",
"status",
lambda: "OK"
)

@app.add_url_rule(
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


print("INICIANDO HILO CTRADER")

threading.Thread(
target=iniciar_ctrader,
daemon=True
).start()
