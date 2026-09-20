import os
import threading

from flask import Flask, request

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
ProtoOAApplicationAuthReq,
ProtoOAGetAccountListByAccessTokenReq,
ProtoOAAccountAuthReq,
)
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
ProtoOAGetAccountListByAccessTokenRes,
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

# ============================================================
# VARIABLES INTERNAS
# ============================================================

ctrader_client = None
account_id = None
account_authenticated = False


# ============================================================
# CONEXIÓN A CTRADER DEMO
# ============================================================

def conectar_ctrader():

global ctrader_client

if not CLIENT_ID:
print("ERROR: falta CTRADER_CLIENT_ID")

if not CLIENT_SECRET:
print("ERROR: falta CTRADER_CLIENT_SECRET")

if not ACCESS_TOKEN:
print("ERROR: falta CTRADER_ACCESS_TOKEN")

if not CLIENT_ID or not CLIENT_SECRET or not ACCESS_TOKEN:
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


# ============================================================
# CUANDO CTRADER CONECTA
# ============================================================

def on_connected(client):

print("================================")
print("CONEXIÓN CON CTRADER DEMO OK")
print("================================")

request_auth = ProtoOAApplicationAuthReq()

request_auth.clientId = CLIENT_ID
request_auth.clientSecret = CLIENT_SECRET

client.send(request_auth)


# ============================================================
# CUANDO CTRADER SE DESCONECTA
# ============================================================

def on_disconnected(client, reason):

global account_authenticated

account_authenticated = False

print("================================")
print("CTRADER DESCONECTADO")
print("Motivo:", reason)
print("================================")


# ============================================================
# MENSAJES RECIBIDOS DESDE CTRADER
# ============================================================

def on_message(client, message):

global account_id
global account_authenticated

try:

# ----------------------------------------------------
# RESPUESTA DE AUTENTICACIÓN DE LA APLICACIÓN
# ----------------------------------------------------

if message.payloadType == ProtoOAApplicationAuthReq().payloadType:

print("Aplicación autenticada.")

request_accounts = ProtoOAGetAccountListByAccessTokenReq()

request_accounts.accessToken = ACCESS_TOKEN

print("Solicitando cuentas autorizadas...")

client.send(request_accounts)

return

# ----------------------------------------------------
# LISTA DE CUENTAS AUTORIZADAS
# ----------------------------------------------------

if message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:

response = Protobuf.extract(message)

print("================================")
print("CUENTAS AUTORIZADAS")
print("================================")

cuentas = response.ctidTraderAccount

if not cuentas:

print("NO SE ENCONTRARON CUENTAS AUTORIZADAS.")
return

# Como dejamos autorizada una sola cuenta DEMO,
# utilizamos esa cuenta.

account_id = int(cuentas[0].ctidTraderAccountId)

print("ctidTraderAccountId:", account_id)

print("================================")
print("AUTORIZANDO CUENTA...")
print("================================")

request_account_auth = ProtoOAAccountAuthReq()

request_account_auth.ctidTraderAccountId = account_id
request_account_auth.accessToken = ACCESS_TOKEN

client.send(request_account_auth)

return

# ----------------------------------------------------
# RESPUESTA DE AUTORIZACIÓN DE LA CUENTA
# ----------------------------------------------------

if message.payloadType == ProtoOAAccountAuthRes().payloadType:

response = Protobuf.extract(message)

account_authenticated = True

print("================================")
print("CUENTA CTRADER AUTORIZADA")
print("================================")

print(
"ctidTraderAccountId:",
response.ctidTraderAccountId
)

print("LISTO PARA RECIBIR SEÑALES.")
print("================================")

return

# ----------------------------------------------------
# OTROS MENSAJES
# ----------------------------------------------------

response = Protobuf.extract(message)

print("Mensaje recibido desde cTrader:")
print(response)

except Exception as e:

print("ERROR PROCESANDO MENSAJE CTRADER:")
print(e)


# ============================================================
# WEB
# ============================================================

@app.route("/")
def home():

return "Servidor TradingView cTrader funcionando"


@app.route("/status")
def status():

if account_authenticated:
return "OK - cTrader conectado y cuenta autorizada"

return "OK - servidor funcionando, cTrader aún no autorizado"


# ============================================================
# WEBHOOK TRADINGVIEW
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():

mensaje = request.get_data(as_text=True).strip()

print("================================")
print("WEBHOOK RECIBIDO")
print("Mensaje recibido:", mensaje)
print("================================")

if not mensaje:

return "Mensaje vacío", 400

# --------------------------------------------------------
# IMPORTANTE:
# TODAVÍA NO EJECUTAMOS OPERACIONES.
# --------------------------------------------------------

mensaje_mayusculas = mensaje.upper()

if "COMPRA NASDAQ" in mensaje_mayusculas:

print("SEÑAL DETECTADA: COMPRA NASDAQ")

elif "VENTA NASDAQ" in mensaje_mayusculas:

print("SEÑAL DETECTADA: VENTA NASDAQ")

elif "COMPRA XAUUSD" in mensaje_mayusculas:

print("SEÑAL DETECTADA: COMPRA XAUUSD")

elif "VENTA XAUUSD" in mensaje_mayusculas:

print("SEÑAL DETECTADA: VENTA XAUUSD")

else:

print("SEÑAL NO RECONOCIDA")

print("PRUEBA: NO SE EJECUTARÁ NINGUNA ORDEN.")
print("================================")

return "Webhook recibido correctamente", 200


# ============================================================
# ARRANQUE
# ============================================================

def iniciar_ctrader():

conectar_ctrader()


threading.Thread(
target=iniciar_ctrader,
daemon=True
).start()


# ============================================================
# FLASK
# ============================================================

if __name__ == "__main__":

port = int(os.environ.get("PORT", 10000))

app.run(
host="0.0.0.0",
port=port
)
