import os
import re
import threading
import time

from flask import Flask, request, jsonify

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints

from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAApplicationAuthRes,
    ProtoOAAccountAuthReq,
    ProtoOAAccountAuthRes,
    ProtoOANewOrderReq,
    ProtoOANewOrderRes,
)

from ctrader_open_api.messages.OpenApiModelMessages_pb2 import (
    ProtoOATradeSide,
)

from twisted.internet import reactor


app = Flask(__name__)


# ============================================================
# CONFIGURACION
# ============================================================

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

ACCOUNT_ID = 48481130

# cTrader Demo
HOST = EndPoints.PROTOBUF_DEMO_HOST
PORT = EndPoints.PROTOBUF_PORT


# ============================================================
# SIMBOLOS
# ============================================================

SYMBOLS = {
    "NAS100": {
        "id": 10014,
        "volume": 10,
    },
    "XAUUSD": {
        "id": 41,
        "volume": 100,
    },
}


# ============================================================
# ESTADO CTRADER
# ============================================================

ctrader_client = None

ctrader_connected = False
application_authenticated = False
account_authenticated = False

reactor_started = False

state_lock = threading.Lock()


# ============================================================
# FUNCIONES DE ESTADO
# ============================================================

def set_state(name, value):
    global ctrader_connected
    global application_authenticated
    global account_authenticated

    with state_lock:
        if name == "connected":
            ctrader_connected = value

        elif name == "application":
            application_authenticated = value

        elif name == "account":
            account_authenticated = value


# ============================================================
# ERROR CTRADER
# ============================================================

def on_ctrader_error(failure):
    print("=================================")
    print("CTRADER: ERROR")
    print(failure)
    print("=================================")


# ============================================================
# CONEXION CTRADER
# ============================================================

def on_connected(client):
    print("=================================")
    print("CTRADER: CONECTADO")
    print("=================================")

    set_state("connected", True)

    authenticate_application(client)


# ============================================================
# DESCONEXION CTRADER
# ============================================================

def on_disconnected(client, reason):
    print("=================================")
    print("CTRADER: DESCONECTADO")
    print("RAZON:", reason)
    print("=================================")

    set_state("connected", False)
    set_state("application", False)
    set_state("account", False)


# ============================================================
# AUTENTICAR APLICACION
# ============================================================

def authenticate_application(client):
    print("CTRADER: AUTENTICANDO APLICACION")

    request_message = ProtoOAApplicationAuthReq()

    request_message.clientId = CLIENT_ID
    request_message.clientSecret = CLIENT_SECRET

    deferred = client.send(request_message)

    deferred.addCallbacks(
        on_application_authenticated,
        on_ctrader_error
    )


def on_application_authenticated(response):
    print("=================================")
    print("CTRADER: APLICACION AUTENTICADA")
    print("=================================")

    set_state("application", True)

    authenticate_account()


# ============================================================
# AUTENTICAR CUENTA
# ============================================================

def authenticate_account():
    global ctrader_client

    print("CTRADER: AUTENTICANDO CUENTA")
    print("CUENTA:", ACCOUNT_ID)

    request_message = ProtoOAAccountAuthReq()

    request_message.ctidTraderAccountId = ACCOUNT_ID
    request_message.accessToken = ACCESS_TOKEN

    deferred = ctrader_client.send(request_message)

    deferred.addCallbacks(
        on_account_authenticated,
        on_ctrader_error
    )


def on_account_authenticated(response):
    print("=================================")
    print("CTRADER: CUENTA AUTENTICADA")
    print("CUENTA:", ACCOUNT_ID)
    print("=================================")

    set_state("account", True)

    print("=================================")
    print("CTRADER: CLIENTE LISTO PARA OPERAR")
    print("=================================")


# ============================================================
# INICIAR CTRADER
# ============================================================

def start_ctrader():

    global ctrader_client
    global reactor_started

    print("=================================")
    print("INICIANDO CTRADER")
    print("=================================")

    print("CTRADER: VARIABLES ENCONTRADAS")
    print("CLIENT ID PRESENTE:", bool(CLIENT_ID))
    print("CLIENT SECRET PRESENTE:", bool(CLIENT_SECRET))
    print("ACCESS TOKEN PRESENTE:", bool(ACCESS_TOKEN))

    if not CLIENT_ID:
        print("CTRADER: FALTA CTRADER_CLIENT_ID")
        return

    if not CLIENT_SECRET:
        print("CTRADER: FALTA CTRADER_CLIENT_SECRET")
        return

    if not ACCESS_TOKEN:
        print("CTRADER: FALTA CTRADER_ACCESS_TOKEN")
        return

    try:
        print("CTRADER: CREANDO CLIENTE DEMO")

        ctrader_client = Client(
            HOST,
            PORT,
            TcpProtocol
        )

        print("CTRADER: CLIENTE CREADO")

        ctrader_client.setConnectedCallback(on_connected)
        ctrader_client.setDisconnectedCallback(on_disconnected)

        print("CTRADER: CALLBACKS CONFIGURADOS")

        def start_client_service():

            print("=================================")
            print("CTRADER: INICIANDO SERVICIO")
            print("=================================")

            try:
                ctrader_client.startService()

                print("CTRADER: SERVICIO INICIADO")

            except Exception as error:
                print("CTRADER: ERROR AL INICIAR SERVICIO")
                print(error)

        print("CTRADER: ESPERANDO REACTOR")

        reactor.callWhenRunning(start_client_service)

        if not reactor_started:

            reactor_started = True

            print("=================================")
            print("CTRADER: INICIANDO REACTOR")
            print("=================================")

            reactor.run(installSignalHandlers=False)

    except Exception as error:

        print("=================================")
        print("CTRADER: ERROR GENERAL")
        print(error)
        print("=================================")


# ============================================================
# LANZAR CTRADER EN SEGUNDO PLANO
# ============================================================

def launch_ctrader():

    thread = threading.Thread(
        target=start_ctrader,
        daemon=True
    )

    thread.start()

    print("CTRADER: HILO DE CONEXION INICIADO")


# ============================================================
# PARSEAR MENSAJE DE TRADINGVIEW
# ============================================================

def parse_alert(message):

    if not message:
        return None

    text = message.upper().strip()

    symbol = None
    side = None

    # -----------------------------------------
    # SIMBOLO
    # -----------------------------------------

    if "XAUUSD" in text:
        symbol = "XAUUSD"

    elif "NAS100" in text:
        symbol = "NAS100"

    elif "NASDAQ" in text:
        symbol = "NAS100"

    # -----------------------------------------
    # DIRECCION
    # -----------------------------------------

    if "VENTA" in text or "SELL" in text:
        side = "SELL"

    elif "COMPRA" in text or "BUY" in text:
        side = "BUY"

    # -----------------------------------------
    # PRECIO DE CONFIRMACION
    # -----------------------------------------

    price = None

    match = re.search(
        r"CONFIRMACI[ÓO]N\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
        text
    )

    if match:
        try:
            price = float(match.group(1))
        except Exception:
            price = None

    if symbol is None or side is None:
        return None

    return {
        "symbol": symbol,
        "side": side,
        "price": price,
    }


# ============================================================
# ABRIR OPERACION
# ============================================================

def open_market_order(symbol, side):

    global ctrader_client

    print("=================================")
    print("CTRADER: INTENTANDO ABRIR OPERACION")
    print("=================================")

    if ctrader_client is None:
        print("CTRADER: CLIENTE NO CREADO")
        return {
            "success": False,
            "error": "cliente_no_creado"
        }

    with state_lock:

        connected = ctrader_connected
        app_auth = application_authenticated
        account_auth = account_authenticated

    print("CTRADER: CONECTADO:", connected)
    print("CTRADER: APLICACION AUTENTICADA:", app_auth)
    print("CTRADER: CUENTA AUTENTICADA:", account_auth)

    if not connected:
        print("CTRADER: ERROR - NO ESTA CONECTADO")

        return {
            "success": False,
            "error": "ctrader_no_conectado"
        }

    if not app_auth:
        print("CTRADER: ERROR - APLICACION NO AUTENTICADA")

        return {
            "success": False,
            "error": "aplicacion_no_autenticada"
        }

    if not account_auth:
        print("CTRADER: ERROR - CUENTA NO AUTENTICADA")

        return {
            "success": False,
            "error": "cuenta_no_autenticada"
        }

    if symbol not in SYMBOLS:
        print("CTRADER: SIMBOLO NO CONFIGURADO:", symbol)

        return {
            "success": False,
            "error": "simbolo_no_configurado"
        }

    symbol_id = SYMBOLS[symbol]["id"]
    volume = SYMBOLS[symbol]["volume"]

    if side == "BUY":
        trade_side = ProtoOATradeSide.BUY
    else:
        trade_side = ProtoOATradeSide.SELL

    print("SIMBOLO:", symbol)
    print("SYMBOL ID:", symbol_id)
    print("VOLUMEN:", volume)
    print("LOTES:", volume / 1000)
    print("LADO:", side)
    print("CUENTA:", ACCOUNT_ID)

    request_message = ProtoOANewOrderReq()

    request_message.ctidTraderAccountId = ACCOUNT_ID
    request_message.symbolId = symbol_id
    request_message.orderType = 1
    request_message.tradeSide = trade_side
    request_message.volume = volume

    print("CTRADER: ENVIANDO ORDEN")

    try:

        deferred = ctrader_client.send(request_message)

        deferred.addCallbacks(
            on_order_response,
            on_ctrader_error
        )

        return {
            "success": True,
            "message": "orden_enviada"
        }

    except Exception as error:

        print("CTRADER: ERROR ENVIANDO ORDEN")
        print(error)

        return {
            "success": False,
            "error": str(error)
        }


# ============================================================
# RESPUESTA DE ORDEN
# ============================================================

def on_order_response(response):

    print("=================================")
    print("CTRADER: RESPUESTA DE ORDEN")
    print("=================================")

    try:
        print(response)

    except Exception as error:
        print("CTRADER: ERROR MOSTRANDO RESPUESTA")
        print(error)


# ============================================================
# WEBHOOK
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    print("=================================")
    print("WEBHOOK RECIBIDO")
    print("=================================")

    try:

        data = request.get_json(
            silent=True
        )

        message = ""

        if isinstance(data, dict):

            message = (
                data.get("message")
                or data.get("text")
                or data.get("alert")
                or ""
            )

        if not message:

            raw_data = request.get_data(
                as_text=True
            )

            message = raw_data

        print("Mensaje recibido:", message)

        parsed = parse_alert(message)

        if parsed is None:

            print("WEBHOOK: NO SE PUDO INTERPRETAR EL MENSAJE")

            return jsonify({
                "success": False,
                "error": "mensaje_no_reconocido"
            }), 400

        print("=================================")
        print("ALERTA INTERPRETADA")
        print("SIMBOLO:", parsed["symbol"])
        print("LADO:", parsed["side"])
        print("PRECIO:", parsed["price"])
        print("=================================")

        result = open_market_order(
            parsed["symbol"],
            parsed["side"]
        )

        return jsonify({
            "success": True,
            "alerta": parsed,
            "resultado": result
        }), 200

    except Exception as error:

        print("=================================")
        print("WEBHOOK: ERROR")
        print(error)
        print("=================================")

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ============================================================
# PAGINA PRINCIPAL
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return """
    =================================
    TradingView cTrader
    =================================

    Servidor funcionando correctamente.
    """


# ============================================================
# ESTADO
# ============================================================

@app.route("/status", methods=["GET"])
def status():

    with state_lock:

        return jsonify({
            "cliente_creado": ctrader_client is not None,
            "conectado": ctrader_connected,
            "aplicacion_autenticada": application_authenticated,
            "cuenta_autenticada": account_authenticated,
            "cuenta": ACCOUNT_ID
        })


# ============================================================
# INICIO
# ============================================================

print("=================================")
print("TRADINGVIEW CTRADER")
print("INICIANDO SERVIDOR")
print("=================================")

launch_ctrader()
