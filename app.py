import os
import re
import threading
import time
from flask import Flask, request, jsonify

from ctrader_open_api import Client, Protobuf, TcpProtocol, Auth, EndPoints

from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

from twisted.internet import reactor


# ============================================================
# CONFIGURACIÓN
# ============================================================

app = Flask(__name__)

CLIENT_ID = os.environ.get("TRADING_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TRADING_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("TRADING_REDIRECT_URI")

# DEMO SIEMPRE PARA ESTA PRIMERA PRUEBA
HOST = EndPoints.PROTOBUF_DEMO_HOST

# Lotaje inicial de prueba
NAS100_LOTS = 0.01
XAUUSD_LOTS = 0.01

# Cierre por invalidación
ENABLE_INVALIDATION_CLOSE = True

# Si True, una nueva señal puede volver a abrir una operación
# después de que la anterior haya sido cerrada.
ENABLE_REENTRY = True

# Identificador de nuestras operaciones
ORDER_LABEL = "TV_CTRADER_TEST"


# ============================================================
# VARIABLES INTERNAS
# ============================================================

access_token = None
refresh_token = None

current_account_id = None

client = None
client_ready = False

symbol_ids = {}

positions = {}

reactor_started = False


# ============================================================
# PÁGINA PRINCIPAL
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
<p>Cuenta demo: activa para esta prueba.</p>
<p>Webhook: /webhook</p>
<p>Callback OAuth: /callback</p>
</body>
</html>
"""


# ============================================================
# OAUTH
# ============================================================

@app.route("/login")
def login():

if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
return """
<h3>Faltan variables de entorno.</h3>
<p>Revisá TRADING_CLIENT_ID, TRADING_CLIENT_SECRET y
TRADING_REDIRECT_URI en Render.</p>
""", 500

auth = Auth(
CLIENT_ID,
CLIENT_SECRET,
REDIRECT_URI
)

auth_url = auth.getAuthUri()

return f"""
<html>
<body>
<h2>Autorizar cTrader</h2>
<p>Hacé clic:</p>
<a href="{auth_url}">AUTORIZAR CUENTA DEMO</a>
</body>
</html>
"""


@app.route("/callback")
def callback():

global access_token
global refresh_token

code = request.args.get("code")

if not code:
return "No se recibió código de autorización.", 400

try:

auth = Auth(
CLIENT_ID,
CLIENT_SECRET,
REDIRECT_URI
)

token = auth.getToken(code)

access_token = token.get("accessToken")
refresh_token = token.get("refreshToken")

if not access_token:
return "No se obtuvo accessToken.", 500

print("====================================")
print("OAUTH CORRECTO")
print("Access token recibido.")
print("====================================")

start_ctrader()

return """
<html>
<body>
<h2>Autorización correcta</h2>
<p>cTrader fue autorizado.</p>
<p>Podés volver a TradingView.</p>
</body>
</html>
"""

except Exception as e:

print("ERROR OAUTH:", repr(e))

return f"""
Error durante OAuth:
{str(e)}
""", 500


# ============================================================
# CONEXIÓN cTRADER
# ============================================================

def start_ctrader():

global client
global reactor_started

if not access_token:
print("No hay access token.")
return

if client is not None:
print("Cliente cTrader ya iniciado.")
return

print("Iniciando conexión con cTrader Demo...")

client = Client(
HOST,
EndPoints.PROTOBUF_PORT,
TcpProtocol
)

client.setConnectedCallback(on_connected)
client.setDisconnectedCallback(on_disconnected)
client.setMessageReceivedCallback(on_message)

client.startService()

if not reactor_started:

reactor_started = True

thread = threading.Thread(
target=reactor.run,
daemon=True
)

thread.start()


# ============================================================
# CONEXIÓN ESTABLECIDA
# ============================================================

def on_connected(client_instance):

global client_ready

print("====================================")
print("CONECTADO A cTRADER DEMO")
print("====================================")

request_msg = ProtoOAApplicationAuthReq()

request_msg.clientId = CLIENT_ID
request_msg.clientSecret = CLIENT_SECRET

deferred = client_instance.send(request_msg)

deferred.addCallback(on_application_auth)
deferred.addErrback(on_error)


def on_application_auth(response):

print("Aplicación cTrader autenticada.")

request_msg = ProtoOAGetAccountListByAccessTokenReq()

request_msg.accessToken = access_token

deferred = client.send(request_msg)

deferred.addCallback(on_account_list)
deferred.addErrback(on_error)


def on_account_list(response):

global current_account_id

print("Cuentas autorizadas recibidas.")

accounts = response.ctidTraderAccount

if not accounts:

print("NO HAY CUENTAS AUTORIZADAS.")
return

# Buscamos primero una cuenta DEMO.
selected = None

for account in accounts:

print(
"Cuenta:",
account.ctidTraderAccountId,
"LIVE:",
getattr(account, "isLive", False)
)

if not getattr(account, "isLive", False):
selected = account
break

# Si por alguna razón no encontramos demo,
# usamos la primera, pero mostramos aviso.
if selected is None:

print("ATENCIÓN: no se encontró cuenta demo.")
print("Se utilizará la primera cuenta autorizada.")

selected = accounts[0]

current_account_id = selected.ctidTraderAccountId

print("====================================")
print("CUENTA SELECCIONADA:")
print(current_account_id)
print("====================================")

request_msg = ProtoOAAccountAuthReq()

request_msg.ctidTraderAccountId = current_account_id
request_msg.accessToken = access_token

deferred = client.send(request_msg)

deferred.addCallback(on_account_auth)
deferred.addErrback(on_error)


def on_account_auth(response):

global client_ready

client_ready = True

print("====================================")
print("CUENTA cTRADER AUTENTICADA")
print("====================================")

# Pedimos todos los símbolos.
request_msg = ProtoOASymbolsListReq()

request_msg.ctidTraderAccountId = current_account_id

deferred = client.send(request_msg)

deferred.addCallback(on_symbols)
deferred.addErrback(on_error)


# ============================================================
# SÍMBOLOS
# ============================================================

def on_symbols(response):

global symbol_ids

print("Recibiendo símbolos de cTrader...")

for symbol in response.symbol:

name = symbol.symbolName.upper()

if name == "NAS100":
symbol_ids["NAS100"] = symbol.symbolId

if name == "XAUUSD":
symbol_ids["XAUUSD"] = symbol.symbolId

print("====================================")
print("SÍMBOLOS ENCONTRADOS")
print(symbol_ids)
print("====================================")

if "NAS100" not in symbol_ids:
print("ADVERTENCIA: NAS100 no encontrado.")

if "XAUUSD" not in symbol_ids:
print("ADVERTENCIA: XAUUSD no encontrado.")

print("BOT LISTO PARA RECIBIR TRADINGVIEW")


# ============================================================
# WEBHOOK TRADINGVIEW
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():

try:

data = request.get_json(
silent=True
)

if data:

texto = str(data)

else:

texto = request.get_data(
as_text=True
)

texto_upper = texto.upper()

print("====================================")
print("WEBHOOK TRADINGVIEW")
print(texto)
print("====================================")

# ----------------------------------------------------
# INSTRUMENTO
# ----------------------------------------------------

if "NAS100" in texto_upper:

instrumento = "NAS100"

elif "XAUUSD" in texto_upper:

instrumento = "XAUUSD"

else:

return jsonify({
"ok": False,
"error": "Instrumento no reconocido"
}), 400

# ----------------------------------------------------
# DIRECCIÓN
# ----------------------------------------------------

if "COMPRA" in texto_upper or "BUY" in texto_upper:

side = "BUY"

elif "VENTA" in texto_upper or "SELL" in texto_upper:

side = "SELL"

else:

return jsonify({
"ok": False,
"error": "COMPRA/VENTA no reconocida"
}), 400

# ----------------------------------------------------
# PRECIO DE CONFIRMACIÓN
# Solo lo guardamos como referencia.
# La orden se ejecuta al precio de mercado.
# ----------------------------------------------------

confirmation_price = extract_confirmation_price(
texto
)

print("Instrumento:", instrumento)
print("Dirección:", side)
print("Confirmación:", confirmation_price)

# ----------------------------------------------------
# ABRIR OPERACIÓN
# ----------------------------------------------------

result = open_trade(
instrumento,
side
)

return jsonify({
"ok": True,
"instrumento": instrumento,
"side": side,
"confirmation_price": confirmation_price,
"resultado": result
}), 200

except Exception as e:

print("ERROR WEBHOOK:", repr(e))

return jsonify({
"ok": False,
"error": str(e)
}), 500


# ============================================================
# EXTRAER PRECIO DE CONFIRMACIÓN
# ============================================================

def extract_confirmation_price(text):

patterns = [
r"confirmaci[oó]n\s*:\s*([0-9]+(?:[.,][0-9]+)?)",
r"confirmacion\s*:\s*([0-9]+(?:[.,][0-9]+)?)"
]

for pattern in patterns:

match = re.search(
pattern,
text,
re.IGNORECASE
)

if match:

value = match.group(1)

value = value.replace(",", ".")

try:
return float(value)
except:
return value

return None


# ============================================================
# ABRIR OPERACIÓN
# ============================================================

def open_trade(instrument, side):

if not client_ready:

print("cTrader todavía no está listo.")

return {
"success": False,
"error": "cTrader no está autenticado"
}

if instrument not in symbol_ids:

return {
"success": False,
"error": f"Símbolo {instrument} no encontrado"
}

if instrument == "NAS100":

lots = NAS100_LOTS

elif instrument == "XAUUSD":

lots = XAUUSD_LOTS

else:

return {
"success": False,
"error": "Instrumento no permitido"
}

symbol_id = symbol_ids[instrument]

# cTrader utiliza volumen en centésimas de unidad
# según el protocolo Open API.
volume = int(lots * 100)

if volume <= 0:

return {
"success": False,
"error": "Lotaje inválido"
}

print("====================================")
print("ABRIENDO OPERACIÓN")
print("Instrumento:", instrument)
print("Side:", side)
print("Lotes:", lots)
print("Symbol ID:", symbol_id)
print("Volume:", volume)
print("====================================")

request_msg = ProtoOANewOrderReq()

request_msg.ctidTraderAccountId = current_account_id

request_msg.symbolId = int(symbol_id)

request_msg.orderType = ProtoOAOrderType.MARKET

request_msg.tradeSide = ProtoOATradeSide.Value(side)

request_msg.volume = volume

request_msg.label = ORDER_LABEL

request_msg.comment = "TradingView"

deferred = client.send(
request_msg
)

deferred.addCallback(
on_new_order_response
)

deferred.addErrback(
on_error
)

return {
"success": True,
"message": "Orden enviada a cTrader",
"instrument": instrument,
"side": side,
"lots": lots
}


# ============================================================
# RESPUESTA DE ORDEN
# ============================================================

def on_new_order_response(response):

print("====================================")
print("RESPUESTA DE cTRADER")
print(response)
print("====================================")

if hasattr(response, "position"):

try:

position_id = response.position.positionId

print(
"POSICIÓN ABIERTA:",
position_id
)

except Exception:
pass


# ============================================================
# MENSAJES DE cTRADER
# ============================================================

def on_message(client_instance, message):

try:

msg = Protobuf.extract(message)

print("cTrader mensaje:", msg)

# ----------------------------------------------------
# AQUÍ RECIBIREMOS EVENTOS DE POSICIONES.
# Más adelante utilizaremos esto para:
#
# - cierre por invalidación
# - break even
# - TP
# - trailing
# - reapertura
# ----------------------------------------------------

except Exception as e:

print("Error procesando mensaje:", e)


# ============================================================
# DESCONECTADO
# ============================================================

def on_disconnected(client_instance, reason):

global client_ready

client_ready = False

print("====================================")
print("cTrader DESCONECTADO")
print(reason)
print("====================================")


# ============================================================
# ERRORES
# ============================================================

def on_error(failure):

print("====================================")
print("ERROR cTRADER")
print(failure)
print("====================================")


# ============================================================
# INICIO DEL SERVIDOR
# ============================================================

if __name__ == "__main__":

print("====================================")
print("TRADINGVIEW → cTRADER")
print("MODO DEMO")
print("====================================")

app.run(
host="0.0.0.0",
port=int(
os.environ.get(
"PORT",
10000
)
)
)
