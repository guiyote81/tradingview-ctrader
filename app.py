import os
import re
import threading

from flask import Flask, request, jsonify

from ctrader_open_api import Client, TcpProtocol, EndPoints, Protobuf

from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAAccountAuthReq,
    ProtoOANewOrderReq,
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

HOST = EndPoints.PROTOBUF_DEMO_HOST
PORT = EndPoints.PROTOBUF_PORT


# ============================================================
# SIMBOLOS
# ============================================================

SYMBOLS = {
    "NAS100": {
        "id": 10014,
        "volume": 10
    },
    "XAUUSD": {
        "id": 41,
        "volume": 100
    }
}


# ============================================================
# VARIABLES GLOBALES
# ============================================================

ctrader_client = None

ctrader_connected = False
application_authenticated = False
account_authenticated = False

reactor_thread_started = False


# ============================================================
# ERROR GENERAL
# ============================================================

def on_error(failure):

    print("=================================")
    print("CTRADER: ERROR")
    print(failure)
    print("=================================")


# ============================================================
# MENSAJES RECIBIDOS
# ============================================================

def on_message_received(client, message):

    try:

        decoded = Protobuf.extract(message)

        print("=================================")
        print("CTRADER: MENSAJE RECIBIDO")
        print(decoded)
        print("=================================")

    except Exception as error:

        print("CTRADER: ERROR LEYENDO MENSAJE")
        print(error)


# ============================================================
# CONECTADO
# ============================================================

def on_connected(client):

    global ctrader_connected

    print("=================================")
    print("CTRADER: CONECTADO")
    print("=================================")

    ctrader_connected = True

    authenticate_application(client)


# ============================================================
# DESCONECTADO
# ============================================================

def on_disconnected(client, reason):

    global ctrader_connected
    global application_authenticated
    global account_authenticated

    print("=================================")
    print("CTRADER: DESCONECTADO")
    print("RAZON:")
    print(reason)
    print("=================================")

    ctrader_connected = False
    application_authenticated = False
    account_authenticated = False


# ============================================================
# AUTENTICAR APLICACION
# ============================================================

def authenticate_application(client):

    print("=================================")
    print("CTRADER: AUTENTICANDO APLICACION")
    print("=================================")

    request_message = ProtoOAApplicationAuthReq()

    request_message.clientId = CLIENT_ID
    request_message.clientSecret = CLIENT_SECRET

    deferred = client.send(request_message)

    deferred.addCallbacks(
        application_auth_success,
        on_error
    )


def application_auth_success(response):

    global application_authenticated

    print("=================================")
    print("CTRADER: APLICACION AUTENTICADA")
    print("=================================")

    application_authenticated = True

    authenticate_account()


# ============================================================
# AUTENTICAR CUENTA
# ============================================================

def authenticate_account():

    global ctrader_client

    print("=================================")
    print("CTRADER: AUTENTICANDO CUENTA")
    print("CUENTA:", ACCOUNT_ID)
    print("=================================")

    request_message = ProtoOAAccountAuthReq()

    request_message.ctidTraderAccountId = ACCOUNT_ID
    request_message.accessToken = ACCESS_TOKEN

    deferred = ctrader_client.send(request_message)

    deferred.addCallbacks(
        account_auth_success,
        on_error
    )


def account_auth_success(response):

    global account_authenticated

    print("=================================")
    print("CTRADER: CUENTA AUTENTICADA")
    print("CUENTA:", ACCOUNT_ID)
    print("=================================")

    account_authenticated = True

    print("=================================")
    print("CTRADER: CLIENTE LISTO PARA OPERAR")
    print("=================================")


# ============================================================
# INICIAR CTRADER
# ============================================================

def start_ctrader():

    global ctrader_client

    print("=================================")
    print("INICIANDO CTRADER")
    print("=================================")

    print("CTRADER: VARIABLES")
    print("CLIENT ID PRESENTE:", bool(CLIENT_ID))
    print("CLIENT SECRET PRESENTE:", bool(CLIENT_SECRET))
    print("ACCESS TOKEN PRESENTE:", bool(ACCESS_TOKEN))
    print("CUENTA:", ACCOUNT_ID)

    if not CLIENT_ID:

        print("CTRADER: ERROR - FALTA CLIENT ID")
        return

    if not CLIENT_SECRET:

        print("CTRADER: ERROR - FALTA CLIENT SECRET")
        return

    if not ACCESS_TOKEN:

        print("CTRADER: ERROR - FALTA ACCESS TOKEN")
        return

    try:

        print("CTRADER: CREANDO CLIENTE DEMO")

        ctrader_client = Client(
            HOST,
            PORT,
            TcpProtocol
        )

        print("CTRADER: CLIENTE CREADO")

        ctrader_client.setConnectedCallback(
            on_connected
        )

        ctrader_client.setDisconnectedCallback(
            on_disconnected
        )

        ctrader_client.setMessageReceivedCallback(
            on_message_received
        )

        print("CTRADER: CALLBACKS CONFIGURADOS")

        print("CTRADER: INICIANDO SERVICIO")

        ctrader_client.startService()

        print("CTRADER: SERVICIO INICIADO")

        print("=================================")
        print("CTRADER: INICIANDO REACTOR")
        print("=================================")

        reactor.run(
            installSignalHandlers=False
        )

    except Exception as error:

        print("=================================")
        print("CTRADER: ERROR AL INICIAR")
        print(error)
        print("=================================")


# ============================================================
# LANZAR CTRADER
# ============================================================

def launch_ctrader():

    global reactor_thread_started

    if reactor_thread_started:

        print("CTRADER: REACTOR YA INICIADO")
        return

    reactor_thread_started = True

    thread = threading.Thread(
        target=start_ctrader,
        daemon=True
    )

    thread.start()

    print("CTRADER: HILO INICIADO")


# ============================================================
# PARSEAR ALERTA
# ============================================================

def parse_alert(message):

    if not message:

        return None

    text = message.upper().strip()

    symbol = None
    side = None
    price = None

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
    # PRECIO
    # -----------------------------------------

    match = re.search(
        r"CONFIRMACI[ÓO]N\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
        text
    )

    if match:

        try:

            price = float(
                match.group(1)
            )

        except Exception:

            price = None

    if symbol is None or side is None:

        return None

    return {
        "symbol": symbol,
        "side": side,
        "price": price
    }


# ============================================================
# ABRIR ORDEN
# ============================================================

def open_market_order(symbol, side):

    global ctrader_client

    print("=================================")
    print("CTRADER: INTENTANDO ABRIR OPERACION")
    print("=================================")

    print("SIMBOLO:", symbol)
    print("LADO:", side)
    print("CUENTA:", ACCOUNT_ID)

    if ctrader_client is None:

        print("CTRADER: ERROR - CLIENTE NO CREADO")

        return {
            "success": False,
            "error": "cliente_no_creado"
        }

    if not ctrader_connected:

        print("CTRADER: ERROR - NO CONECTADO")

        return {
            "success": False,
            "error": "no_conectado"
        }

    if not application_authenticated:

        print("CTRADER: ERROR - APLICACION NO AUTENTICADA")

        return {
            "success": False,
            "error": "aplicacion_no_autenticada"
        }

    if not account_authenticated:

        print("CTRADER: ERROR - CUENTA NO AUTENTICADA")

        return {
            "success": False,
            "error": "cuenta_no_autenticada"
        }

    if symbol not in SYMBOLS:

        print("CTRADER: ERROR - SIMBOLO NO CONFIGURADO")

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

    print("SYMBOL ID:", symbol_id)
    print("VOLUMEN:", volume)
    print("LOTES:", volume / 1000)
    print("LADO:", side)

    request_message = ProtoOANewOrderReq()

    request_message.ctidTraderAccountId = ACCOUNT_ID
    request_message.symbolId = symbol_id
    request_message.orderType = 1
    request_message.tradeSide = trade_side
    request_message.volume = volume

    print("CTRADER: ENVIANDO ORDEN")

    deferred = ctrader_client.send(
        request_message
    )

    deferred.addCallbacks(
        order_success,
        on_error
    )

    return {
        "success": True,
        "message": "orden_enviada"
    }


# ============================================================
# RESPUESTA ORDEN
# ============================================================

def order_success(response):

    print("=================================")
    print("CTRADER: ORDEN RESPONDIDA")
    print("=================================")

    try:

        print(
            Protobuf.extract(response)
        )

    except Exception:

        print(response)


# ============================================================
# WEBHOOK
# ============================================================

@app.route(
    "/webhook",
    methods=["POST"]
)
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

            message = request.get_data(
                as_text=True
            )

        print("Mensaje recibido:", message)

        parsed = parse_alert(
            message
        )

        if parsed is None:

            print("CTRADER: ALERTA NO RECONOCIDA")

            return jsonify({
                "success": False,
                "error": "alerta_no_reconocida"
            }), 400

        print("=================================")
        print("CTRADER: ALERTA", parsed["symbol"], parsed["side"])
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

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return "Servidor TradingView cTrader funcionando"


# ============================================================
# ESTADO
# ============================================================

@app.route(
    "/status",
    methods=["GET"]
)
def status():

    return jsonify({

        "cliente_creado":
            ctrader_client is not None,

        "conectado":
            ctrader_connected,

        "aplicacion_autenticada":
            application_authenticated,

        "cuenta_autenticada":
            account_authenticated,

        "cuenta":
            ACCOUNT_ID
    })


# ============================================================
# INICIO
# ============================================================

print("=================================")
print("TRADINGVIEW CTRADER")
print("INICIANDO SERVIDOR")
print("=================================")

launch_ctrader()
