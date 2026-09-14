import os
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
# DATOS DE cTRADER
# ============================================================

CLIENT_ID = os.environ.get("TRADING_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TRADING_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("TRADING_REDIRECT_URI")


# ============================================================
# CONFIGURACION
# ============================================================

NAS100_LOTS = float(
os.environ.get("NAS100_LOTS", "0.01")
)

XAUUSD_LOTS = float(
os.environ.get("XAUUSD_LOTS", "0.01")
)

BOT_LABEL = os.environ.get(
"BOT_LABEL",
"TV_SR_M30"
)


# ============================================================
# VARIABLES GLOBALES
# ============================================================

ctrader_client = None

access_token = None

account_id = None

account_authorized = False

ctrader_started = False

symbols_loaded = False

symbols = {}

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

<p>Servidor funcionando correctamente.</p>

<p>
<a href="/login">
Autorizar cTrader
</a>
</p>

<p>
<a href="/status">
Ver estado
</a>
</p>

</body>
</html>
"""


# ============================================================
# LOGIN
# ============================================================

@app.route("/login")
def login():

auth = Auth(
CLIENT_ID,
CLIENT_SECRET,
REDIRECT_URI
)

url = auth.getAuthUrl()

logger.info(
"Redirigiendo a cTrader para autorización."
)

return redirect(url)


# ============================================================
# CALLBACK
# ============================================================

@app.route("/callback")
def callback():

global access_token

code = request.args.get("code")

if not code:

error = request.args.get(
"error",
"Código de autorización no recibido."
)

return (
f"Error de autorización: {error}",
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

logger.info(
"Token de cTrader obtenido correctamente."
)

start_ctrader()

return """
<html>
<body>

<h2>Autorización correcta</h2>

<p>
cTrader fue autorizado correctamente.
</p>

<p>
Ahora revisá los Logs de Render.
</p>

</body>
</html>
"""

except Exception as e:

logger.exception(
"Error obteniendo token."
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
"cTrader ya estaba iniciado."
)

return

if not access_token:

logger.error(
"No existe access_token."
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

thread = threading.Thread(
target=run_reactor,
daemon=True
)

thread.start()

logger.info(
"Cliente cTrader iniciado."
)

except Exception:

logger.exception(
"Error iniciando cTrader."
)


# ============================================================
# REACTOR
# ============================================================

def run_reactor():

try:

if not reactor.running:

reactor.run(
installSignalHandlers=False
)

except Exception:

logger.exception(
"Error ejecutando Twisted."
)


# ============================================================
# CONECTADO
# ============================================================

def on_connected(client):

logger.info(
"CONEXIÓN cTRADER ESTABLECIDA."
)

request = ProtoOAApplicationAuthReq()

request.clientId = CLIENT_ID

request.clientSecret = CLIENT_SECRET

client.send(request)

logger.info(
"Autorización de aplicación enviada."
)


# ============================================================
# DESCONECTADO
# ============================================================

def on_disconnected(client, reason):

logger.warning(
f"cTrader desconectado: {reason}"
)


# ============================================================
# MENSAJES
# ============================================================

def on_message(client, message):

try:

payload_type = message.payloadType

logger.info(
f"Mensaje recibido de cTrader: {payload_type}"
)

if payload_type == ProtoOAPayloadType.PROTO_OA_APPLICATION_AUTH_RES:

on_application_auth(
client,
message
)

elif payload_type == ProtoOAPayloadType.PROTO_OA_GET_ACCOUNT_LIST_BY_ACCESS_TOKEN_RES:

on_account_list(
client,
message
)

elif payload_type == ProtoOAPayloadType.PROTO_OA_ACCOUNT_AUTH_RES:

on_account_auth(
client,
message
)

elif payload_type == ProtoOAPayloadType.PROTO_OA_SYMBOLS_LIST_RES:

on_symbols(
client,
message
)

elif payload_type == ProtoOAPayloadType.PROTO_OA_SYMBOL_BY_ID_RES:

on_symbols_details(
client,
message
)

elif payload_type == ProtoOAPayloadType.PROTO_OA_EXECUTION_EVENT:

on_execution_event(
client,
message
)

elif payload_type == ProtoOAPayloadType.ERROR_RES:

logger.error(
f"ERROR DE cTRADER: {message}"
)

except Exception:

logger.exception(
"Error procesando mensaje."
)


# ============================================================
# AUTORIZACIÓN DE APLICACIÓN
# ============================================================

def on_application_auth(client, message):

logger.info(
"APLICACIÓN cTRADER AUTORIZADA."
)

request = ProtoOAGetAccountListByAccessTokenReq()

request.accessToken = access_token

client.send(request)

logger.info(
"Solicitando cuentas."
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
"NO SE ENCONTRARON CUENTAS."
)

return

logger.info(
f"Cuentas encontradas: {len(accounts)}"
)

selected_account = None

for account in accounts:

logger.info(
f"Cuenta: "
f"{account.ctidTraderAccountId} "
f"Live={account.isLive}"
)

if not account.isLive:

selected_account = account

break

if selected_account is None:

selected_account = accounts[0]

account_id = (
selected_account.ctidTraderAccountId
)

logger.info(
f"CUENTA SELECCIONADA: {account_id}"
)

request = ProtoOAAccountAuthReq()

request.ctidTraderAccountId = account_id

request.accessToken = access_token

client.send(request)

logger.info(
"Autorización de cuenta enviada."
)


# ============================================================
# CUENTA AUTORIZADA
# ============================================================

def on_account_auth(client, message):

global account_authorized

response = Protobuf.extract(
message
)

account_authorized = True

logger.info(
f"CUENTA AUTORIZADA: "
f"{response.ctidTraderAccountId}"
)

request = ProtoOASymbolsListReq()

request.ctidTraderAccountId = account_id

request.includeArchivedSymbols = False

client.send(request)

logger.info(
"Solicitando lista de símbolos."
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
f"Símbolos recibidos: "
f"{len(response.symbol)}"
)

symbols = {}

for symbol in response.symbol:

name = symbol.symbolName

if name.upper() == "NAS100":

symbols["NAS100"] = {
"id": symbol.symbolId,
"name": name
}

logger.info(
f"NAS100 ENCONTRADO. ID={symbol.symbolId}"
)

if name.upper() == "XAUUSD":

symbols["XAUUSD"] = {
"id": symbol.symbolId,
"name": name
}

logger.info(
f"XAUUSD ENCONTRADO. ID={symbol.symbolId}"
)

if not symbols:

logger.warning(
"NO SE ENCONTRARON NAS100/XAUUSD."
)

symbols_loaded = True

return

request = ProtoOASymbolByIdReq()

request.ctidTraderAccountId = account_id

for data in symbols.values():

request.symbolId.append(
data["id"]
)

client.send(request)

logger.info(
"Solicitando información completa de símbolos."
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

for name, data in symbols.items():

if data["id"] == symbol.symbolId:

data["details"] = symbol

logger.info(
f"Información completa: "
f"{name}"
)

logger.info(
f"{symbol}"
)

symbols_loaded = True

logger.info(
"SÍMBOLOS CARGADOS CORRECTAMENTE."
)


# ============================================================
# CONVERSIÓN DE LOTES
# ============================================================

def lots_to_volume(symbol_name, lots):

data = symbols.get(
symbol_name
)

if not data:

raise ValueError(
f"Símbolo no encontrado: {symbol_name}"
)

symbol = data.get(
"details"
)

if symbol is None:

raise ValueError(
f"No hay información completa de {symbol_name}"
)

# cTrader utiliza volumen expresado
# en centésimas de unidad.
#
# Para esta primera prueba utilizamos
# el lotSize del símbolo si está disponible.

lot_size = getattr(
symbol,
"lotSize",
0
)

min_volume = getattr(
symbol,
"minVolume",
0
)

step_volume = getattr(
symbol,
"stepVolume",
0
)

if lot_size <= 0:

raise ValueError(
f"lotSize inválido para {symbol_name}"
)

volume = int(
round(
lot_size * lots
)
)

if min_volume > 0 and volume < min_volume:

volume = min_volume

if step_volume > 0:

volume = (
volume // step_volume
) * step_volume

logger.info(
f"{symbol_name}: "
f"{lots} lotes -> "
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

body = request.get_data(
as_text=True
)

logger.info(
"========================================"
)

logger.info(
"WEBHOOK DE TRADINGVIEW RECIBIDO"
)

logger.info(
f"Mensaje: {body}"
)

logger.info(
"========================================"
)

text = body.upper()

# ----------------------------------------------------
# INSTRUMENTO
# ----------------------------------------------------

if "NAS100" in text:

symbol_name = "NAS100"

elif "XAUUSD" in text:

symbol_name = "XAUUSD"

else:

logger.warning(
"Instrumento no reconocido."
)

return jsonify({
"ok": False,
"error": "Instrumento no reconocido"
}), 400

# ----------------------------------------------------
# DIRECCIÓN
# ----------------------------------------------------

if (
"COMPRA" in text
or "BUY" in text
):

side = "BUY"

elif (
"VENTA" in text
or "SELL" in text
):

side = "SELL"

else:

logger.warning(
"COMPRA/VENTA no encontrada."
)

return jsonify({
"ok": False,
"error": "Dirección no reconocida"
}), 400

logger.info(
f"SEÑAL: {side} {symbol_name}"
)

# ----------------------------------------------------
# COMPROBAR CONEXIÓN
# ----------------------------------------------------

if ctrader_client is None:

logger.error(
"cTrader no está conectado."
)

return jsonify({
"ok": False,
"error": "cTrader no conectado"
}), 503

if not account_authorized:

logger.error(
"Cuenta cTrader no autorizada."
)

return jsonify({
"ok": False,
"error": "Cuenta no autorizada"
}), 503

if symbol_name not in symbols:

logger.error(
f"{symbol_name} no está disponible."
)

return jsonify({
"ok": False,
"error": "Símbolo no disponible"
}), 503

# ----------------------------------------------------
# ENVIAR ORDEN
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
"ERROR EN WEBHOOK"
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
f"Símbolo no permitido: {symbol_name}"
)

return

volume = lots_to_volume(
symbol_name,
lots
)

request = ProtoOANewOrderReq()

request.ctidTraderAccountId = account_id

request.symbolId = symbols[
symbol_name
]["id"]

request.orderType = ProtoOAOrderType.Value(
"MARKET"
)

request.tradeSide = ProtoOATradeSide.Value(
side
)

request.volume = volume

request.label = BOT_LABEL

request.comment = (
f"TradingView {side}"
)

logger.info(
"========================================"
)

logger.info(
f"ENVIANDO ORDEN {side}"
)

logger.info(
f"Símbolo: {symbol_name}"
)

logger.info(
f"Lotes: {lots}"
)

logger.info(
f"Volumen cTrader: {volume}"
)

logger.info(
"========================================"
)

ctrader_client.send(
request
)

except Exception:

logger.exception(
"ERROR ENVIANDO ORDEN"
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
"EVENTO DE EJECUCIÓN"
)

logger.info(
f"{response}"
)

logger.info(
"========================================"
)

except Exception:

logger.exception(
"Error procesando ejecución."
)


# ============================================================
# ESTADO
# ============================================================

@app.route("/status")
def status():

return jsonify({
"server": "online",
"ctrader_started": ctrader_started,
"account_authorized": account_authorized,
"symbols_loaded": symbols_loaded,
"account_id": account_id,
"symbols": {
name: data.get("id")
for name, data in symbols.items()
}
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
