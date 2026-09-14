import os
import re
import threading
import logging

from flask import Flask, request, redirect, jsonify

from ctrader_open_api import Client, Protobuf, TcpProtocol, Auth, EndPoints
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

from twisted.internet import reactor


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# VARIABLES DE ENTORNO
# ============================================================

CLIENT_ID = os.environ.get("TRADING_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TRADING_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("TRADING_REDIRECT_URI")

if not CLIENT_ID:
logger.warning("Falta TRADING_CLIENT_ID")

if not CLIENT_SECRET:
logger.warning("Falta TRADING_CLIENT_SECRET")

if not REDIRECT_URI:
logger.warning("Falta TRADING_REDIRECT_URI")


# ============================================================
# CONFIGURACION DE TRADING
# ============================================================

# Lotes que queremos utilizar inicialmente.
# 0.01 = un centésimo de lote.
NAS100_LOTS = float(os.environ.get("NAS100_LOTS", "0.01"))
XAUUSD_LOTS = float(os.environ.get("XAUUSD_LOTS", "0.01"))

BOT_LABEL = os.environ.get(
"BOT_LABEL",
"TV_SR_M30"
)


# ============================================================
# ESTADO GLOBAL
# ============================================================

ctrader_client = None

access_token = None
account_id = None

symbols = {}

ctrader_started = False
account_authorized = False
symbols_loaded = False

state_lock = threading.Lock()


# ============================================================
# PAGINA PRINCIPAL
# ============================================================

@app.route("/")
def home():
return """
<html>
<head>
<title>TradingView cTrader</title>
</head>
<body>
<h2>TradingView → cTrader</h2>

<p>Servidor funcionando.</p>

<p>
<a href="/login">
Autorizar cTrader
</a>
</p>

<p>
Webhook:
<b>/webhook</b>
</p>
</body>
</html>
"""


# ============================================================
# LOGIN cTRADER
# ============================================================

@app.route("/login")
def login():

if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
return (
"Faltan variables de entorno de cTrader.",
500
)

auth = Auth(
CLIENT_ID,
CLIENT_SECRET,
REDIRECT_URI
)

url = auth.getAuthUrl()

logger.info("Redirigiendo a cTrader para autorización.")

return redirect(url)


# ============================================================
# CALLBACK OAUTH
# ============================================================

@app.route("/callback")
def callback():

global access_token

code = request.args.get("code")

if not code:
error = request.args.get("error")

return (
f"Error de autorización cTrader: {error}",
400
)

try:

auth = Auth(
CLIENT_ID,
CLIENT_SECRET,
REDIRECT_URI
)

token = auth.getToken(code)

access_token = token.accessToken

logger.info("Token de cTrader obtenido correctamente.")

start_ctrader()

return """
<html>
<body>
<h2>Autorización correcta</h2>

<p>
cTrader fue autorizado correctamente.
</p>

<p>
Revisá los logs de Render.
</p>

<p>
Ya podés volver a TradingView.
</p>
</body>
</html>
"""

except Exception as e:

logger.exception(
"Error obteniendo token de cTrader."
)

return (
f"Error obteniendo token: {str(e)}",
500
)


# ============================================================
# INICIAR cTRADER
# ============================================================

def start_ctrader():

global ctrader_client
global ctrader_started

with state_lock:

if ctrader_started:
logger.info(
"cTrader ya está iniciado."
)
return

if not access_token:
logger.error(
"No hay access_token."
)
return

try:

logger.info(
"Iniciando conexión con cTrader DEMO..."
)

ctrader_client = Client(
EndPoints.PROTOBUF_DEMO_HOST,
EndPoints.PROTOBUF_PORT,
TcpProtocol
)

ctrader_client.setConnectedCallback(
on_connected
)

ctrader_client.setDisconnectedCallback(
on_disconnected
)

ctrader_client.setMessageReceivedCallback(
on_message
)

ctrader_client.startService()

ctrader_started = True

reactor_thread = threading.Thread(
target=run_reactor,
daemon=True
)

reactor_thread.start()

logger.info(
"Cliente cTrader iniciado."
)

except Exception:

logger.exception(
"Error iniciando cTrader."
)


# ============================================================
# TWISTED REACTOR
# ============================================================

def run_reactor():

try:

if not reactor.running:

reactor.run(
installSignalHandlers=False
)

except Exception:

logger.exception(
"Error ejecutando reactor Twisted."
)


# ============================================================
# CONEXIÓN
# ============================================================

def on_connected(client):

logger.info(
"Conectado al servidor Open API de cTrader."
)

request = ProtoOAApplicationAuthReq()

request.clientId = CLIENT_ID
request.clientSecret = CLIENT_SECRET

client.send(request)

logger.info(
"Solicitud de autorización de aplicación enviada."
)


# ============================================================
# DESCONEXIÓN
# ============================================================

def on_disconnected(client, reason):

logger.warning(
f"cTrader desconectado: {reason}"
)


# ============================================================
# MENSAJES RECIBIDOS
# ============================================================

def on_message(client, message):

try:

payload_type = message.payloadType

logger.info(
f"Mensaje cTrader recibido. payloadType={payload_type}"
)

# ----------------------------------------------------
# AUTORIZACIÓN DE APLICACIÓN
# ----------------------------------------------------

if payload_type == ProtoOAPayloadType.PROTO_OA_APPLICATION_AUTH_RES:

on_application_auth(
client,
message
)

# ----------------------------------------------------
# LISTA DE CUENTAS
# ----------------------------------------------------

elif payload_type == ProtoOAPayloadType.PROTO_OA_GET_ACCOUNT_LIST_BY_ACCESS_TOKEN_RES:

on_account_list(
client,
message
)

# ----------------------------------------------------
# AUTORIZACIÓN DE CUENTA
# ----------------------------------------------------

elif payload_type == ProtoOAPayloadType.PROTO_OA_ACCOUNT_AUTH_RES:

on_account_auth(
client,
message
)

# ----------------------------------------------------
# LISTA DE SÍMBOLOS
# ----------------------------------------------------

elif payload_type == ProtoOAPayloadType.PROTO_OA_SYMBOLS_LIST_RES:

on_symbols(
client,
message
)

# ----------------------------------------------------
# DATOS COMPLETOS DE SÍMBOLOS
# ----------------------------------------------------

elif payload_type == ProtoOAPayloadType.PROTO_OA_SYMBOL_BY_ID_RES:

on_symbols_details(
client,
message
)

# ----------------------------------------------------
# RESPUESTA DE ORDEN
# ----------------------------------------------------

elif payload_type == ProtoOAPayloadType.PROTO_OA_EXECUTION_EVENT:

on_execution_event(
client,
message
)

# ----------------------------------------------------
# ERROR
# ----------------------------------------------------

elif payload_type == ProtoOAPayloadType.ERROR_RES:

logger.error(
f"Error recibido de cTrader: {message}"
)

except Exception:

logger.exception(
"Error procesando mensaje de cTrader."
)


# ============================================================
# AUTORIZACIÓN DE APLICACIÓN
# ============================================================

def on_application_auth(client, message):

logger.info(
"Aplicación cTrader autorizada."
)

request = ProtoOAGetAccountListByAccessTokenReq()

request.accessToken = access_token

client.send(request)

logger.info(
"Solicitando cuentas disponibles."
)


# ============================================================
# LISTA DE CUENTAS
# ============================================================

def on_account_list(client, message):

global account_id

response = Protobuf.extract(
message
)

accounts = response.ctidTraderAccount

if not accounts:

logger.error(
"No se encontraron cuentas cTrader."
)

return

logger.info(
f"Cuentas encontradas: {len(accounts)}"
)

selected_account = None

# Preferimos DEMO.
for account in accounts:

logger.info(
f"Cuenta encontrada: "
f"{account.ctidTraderAccountId} "
f"live={account.isLive}"
)

if not account.isLive:

selected_account = account
break

# Si no hay demo, usamos la primera.
if selected_account is None:

selected_account = accounts[0]

account_id = selected_account.ctidTraderAccountId

logger.info(
f"Cuenta seleccionada: {account_id} "
f"live={selected_account.isLive}"
)

request = ProtoOAAccountAuthReq()

request.ctidTraderAccountId = account_id
request.accessToken = access_token

client.send(request)

logger.info(
"Solicitud de autorización de cuenta enviada."
)


# ============================================================
# AUTORIZACIÓN DE CUENTA
# ============================================================

def on_account_auth(client, message):

global account_authorized

response = Protobuf.extract(
message
)

account_authorized = True

logger.info(
f"Cuenta cTrader autorizada: "
f"{response.ctidTraderAccountId}"
)

request = ProtoOASymbolsListReq()

request.ctidTraderAccountId = account_id

request.includeArchivedSymbols = False

client.send(request)

logger.info(
"Solicitando símbolos disponibles."
)


# ============================================================
# LISTA DE SÍMBOLOS
# ============================================================

def on_symbols(client, message):

global symbols
global symbols_loaded

response = Protobuf.extract(
message
)

logger.info(
f"Se recibieron {len(response.symbol)} símbolos."
)

symbols = {}

requested_names = [
"NAS100",
"XAUUSD"
]

for symbol in response.symbol:

symbol_name = symbol.symbolName

for wanted in requested_names:

if symbol_name.upper() == wanted:

symbols[wanted] = {
"id": symbol.symbolId,
"name": symbol_name
}

logger.info(
f"Símbolo encontrado: "
f"{wanted} "
f"ID={symbol.symbolId}"
)

if "NAS100" not in symbols:

logger.warning(
"NAS100 no fue encontrado."
)

if "XAUUSD" not in symbols:

logger.warning(
"XAUUSD no fue encontrado."
)

symbol_ids = []

for item in symbols.values():

symbol_ids.append(
item["id"]
)

if symbol_ids:

request = ProtoOASymbolByIdReq()

request.ctidTraderAccountId = account_id

request.symbolId.extend(
symbol_ids
)

client.send(request)

logger.info(
"Solicitando información completa de los símbolos."
)

else:

symbols_loaded = True

logger.warning(
"No se encontró ningún símbolo solicitado."
)


# ============================================================
# INFORMACIÓN COMPLETA DE SÍMBOLOS
# ============================================================

def on_symbols_details(client, message):

global symbols_loaded

response = Protobuf.extract(
message
)

for symbol in response.symbol:

symbol_id = symbol.symbolId

for name, data in symbols.items():

if data["id"] == symbol_id:

data["details"] = symbol

if symbol.HasField("lotSize"):

data["lotSize"] = symbol.lotSize

if symbol.HasField("minVolume"):

data["minVolume"] = symbol.minVolume

if symbol.HasField("stepVolume"):

data["stepVolume"] = symbol.stepVolume

logger.info(
f"{name}: "
f"lotSize={data.get('lotSize')} "
f"minVolume={data.get('minVolume')} "
f"stepVolume={data.get('stepVolume')}"
)

symbols_loaded = True

logger.info(
"Información de símbolos cargada."
)


# ============================================================
# CONVERTIR LOTES A VOLUMEN cTRADER
# ============================================================

def lots_to_volume(symbol_name, lots):

data = symbols.get(symbol_name)

if not data:

raise ValueError(
f"No existe información para {symbol_name}"
)

lot_size = data.get("lotSize")

if not lot_size:

raise ValueError(
f"No se pudo obtener lotSize de {symbol_name}"
)

volume = int(
round(
lot_size * lots
)
)

min_volume = data.get(
"minVolume"
)

step_volume = data.get(
"stepVolume"
)

if min_volume and volume < min_volume:

volume = min_volume

if step_volume and step_volume > 0:

volume = (
volume // step_volume
) * step_volume

logger.info(
f"{symbol_name}: "
f"{lots} lotes → "
f"volume={volume}"
)

return volume


# ============================================================
# WEBHOOK TRADINGVIEW
# ============================================================

@app.route(
"/webhook",
methods=["POST"]
)
def webhook():

try:

raw_body = request.get_data(
as_text=True
)

logger.info(
"========================================"
)

logger.info(
"WEBHOOK RECIBIDO DE TRADINGVIEW"
)

logger.info(
f"Contenido: {raw_body}"
)

logger.info(
"========================================"
)

message_text = raw_body.upper()

# ----------------------------------------------------
# DETERMINAR INSTRUMENTO
# ----------------------------------------------------

if "NAS100" in message_text:

symbol_name = "NAS100"

elif "XAUUSD" in message_text:

symbol_name = "XAUUSD"

else:

logger.warning(
"No se encontró NAS100 ni XAUUSD."
)

return jsonify({
"ok": False,
"error": "Instrumento no reconocido"
}), 400

# ----------------------------------------------------
# DETERMINAR DIRECCIÓN
# ----------------------------------------------------

if (
"COMPRA" in message_text
or "BUY" in message_text
):

side = "BUY"

elif (
"VENTA" in message_text
or "SELL" in message_text
):

side = "SELL"

else:

logger.warning(
"No se encontró COMPRA/VENTA."
)

return jsonify({
"ok": False,
"error": "Dirección no reconocida"
}), 400

logger.info(
f"SEÑAL DETECTADA: "
f"{side} {symbol_name}"
)

# ----------------------------------------------------
# VERIFICACIONES
# ----------------------------------------------------

if not ctrader_client:

logger.error(
"cTrader todavía no está conectado."
)

return jsonify({
"ok": False,
"error": "cTrader no conectado"
}), 503

if not account_authorized:

logger.error(
"La cuenta cTrader no está autorizada."
)

return jsonify({
"ok": False,
"error": "Cuenta cTrader no autorizada"
}), 503

if symbol_name not in symbols:

logger.error(
f"Símbolo {symbol_name} no disponible."
)

return jsonify({
"ok": False,
"error": "Símbolo no disponible"
}), 503

# ----------------------------------------------------
# ABRIR OPERACIÓN
# ----------------------------------------------------

open_trade(
symbol_name,
side
)

return jsonify({
"ok": True,
"symbol": symbol_name,
"side": side
}), 200

except Exception as e:

logger.exception(
"Error procesando webhook."
)

return jsonify({
"ok": False,
"error": str(e)
}), 500


# ============================================================
# ABRIR OPERACIÓN
# ============================================================

def open_trade(symbol_name, side):

try:

if symbol_name == "NAS100":

lots = NAS100_LOTS

elif symbol_name == "XAUUSD":

lots = XAUUSD_LOTS

else:

logger.error(
f"Instrumento no permitido: {symbol_name}"
)

return

volume = lots_to_volume(
symbol_name,
lots
)

trade_side = ProtoOATradeSide.Value(
side
)

request = ProtoOANewOrderReq()

request.ctidTraderAccountId = account_id

request.symbolId = symbols[
symbol_name
]["id"]

request.orderType = ProtoOAOrderType.Value(
"MARKET"
)

request.tradeSide = trade_side

request.volume = volume

request.label = BOT_LABEL

request.comment = (
f"TradingView {side}"
)

logger.info(
"----------------------------------------"
)

logger.info(
f"ENVIANDO ORDEN: "
f"{side} {symbol_name}"
)

logger.info(
f"Lotes: {lots}"
)

logger.info(
f"Volumen protocolo: {volume}"
)

logger.info(
"----------------------------------------"
)

ctrader_client.send(
request
)

except Exception:

logger.exception(
"Error enviando orden."
)


# ============================================================
# EVENTO DE EJECUCIÓN
# ============================================================

def on_execution_event(client, message):

try:

response = Protobuf.extract(
message
)

logger.info(
"========================================"
)

logger.info(
"EVENTO DE EJECUCIÓN cTRADER"
)

logger.info(
f"{response}"
)

logger.info(
"========================================"
)

except Exception:

logger.exception(
"Error procesando evento de ejecución."
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/status")
def status():

return jsonify({
"server": "online",
"ctrader_started": ctrader_started,
"account_authorized": account_authorized,
"symbols_loaded": symbols_loaded,
"account_id": account_id,
"symbols": symbols
})


# ============================================================
# EJECUCIÓN LOCAL
# ============================================================

if __name__ == "__main__":

port = int(
os.environ.get(
"PORT",
"10000"
)
)

app.run(
host="0.0.0.0",
port=port
)
