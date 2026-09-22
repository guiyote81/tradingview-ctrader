import os
import re
import time
import multiprocessing

from flask import Flask, request, jsonify

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints

from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAAccountAuthReq,
    ProtoOANewOrderReq,
)

from ctrader_open_api.messages.OpenApiModelMessages_pb2 import (
    ProtoOAOrderType,
    ProtoOATradeSide,
)

from twisted.internet import reactor
from twisted.internet.task import LoopingCall


# ============================================================
# FLASK
# ============================================================

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
# COMUNICACION ENTRE PROCESOS
# ============================================================

order_queue = multiprocessing.Queue()

ctrader_status = multiprocessing.Manager().dict()

ctrader_status["cliente_creado"] = False
ctrader_status["conectado"] = False
ctrader_status["aplicacion_autenticada"] = False
ctrader_status["cuenta_autenticada"] = False


# ============================================================
# PROCESO CTRADER
# ============================================================

def ctrader_process(order_queue, status):

    client = None

    print("=================================")
    print("INICIANDO PROCESO CTRADER")
    print("=================================")

    print("CLIENT ID PRESENTE:", bool(CLIENT_ID))
    print("CLIENT SECRET PRESENTE:", bool(CLIENT_SECRET))
    print("ACCESS TOKEN PRESENTE:", bool(ACCESS_TOKEN))
    print("CUENTA:", ACCOUNT_ID)

    if not CLIENT_ID:
        print("CTRADER: FALTA CLIENT ID")
        return

    if not CLIENT_SECRET:
        print("CTRADER: FALTA CLIENT SECRET")
        return

    if not ACCESS_TOKEN:
        print("CTRADER: FALTA ACCESS TOKEN")
        return

    # ========================================================
    # ERROR
    # ========================================================

    def on_error(failure):

        print("=================================")
        print("CTRADER: ERROR")
        print(failure)
        print("=================================")

    # ========================================================
    # MENSAJES
    # ========================================================

    def on_message_received(client, message):

        try:

            payload = Protobuf.extract(message)

            payload_type = getattr(
                message,
                "payloadType",
                None
            )

            print("=================================")
            print("CTRADER: MENSAJE RECIBIDO")
            print("PAYLOAD TYPE:", payload_type)
            print("=================================")

            # Mostrar errores de orden claramente
            if hasattr(payload, "errorCode"):

                error_code = getattr(
                    payload,
                    "errorCode",
                    ""
                )

                description = getattr(
                    payload,
                    "description",
                    ""
                )

                if error_code:

                    print("CTRADER ERROR CODE:", error_code)
                    print("CTRADER DESCRIPTION:", description)

            # Mostrar ejecucion
            if hasattr(payload, "executionType"):

                print(
                    "CTRADER EXECUTION TYPE:",
                    payload.executionType
                )

        except Exception as error:

            print(
                "CTRADER: ERROR PROCESANDO MENSAJE:",
                error
            )

    # ========================================================
    # CONECTADO
    # ========================================================

    def connected(client):

        print("=================================")
        print("CTRADER: CONECTADO")
        print("=================================")

        status["conectado"] = True

        print("CTRADER: ENVIANDO AUTENTICACION DE APLICACION")

        request_message = ProtoOAApplicationAuthReq()

        request_message.clientId = CLIENT_ID
        request_message.clientSecret = CLIENT_SECRET

        deferred = client.send(
            request_message
        )

        deferred.addCallbacks(
            application_authenticated,
            on_error
        )

    # ========================================================
    # DESCONEXION
    # ========================================================

    def disconnected(client, reason):

        print("=================================")
        print("CTRADER: DESCONECTADO")
        print("RAZON:", reason)
        print("=================================")

        status["conectado"] = False
        status["aplicacion_autenticada"] = False
        status["cuenta_autenticada"] = False

    # ========================================================
    # APLICACION AUTENTICADA
    # ========================================================

    def application_authenticated(response):

        print("=================================")
        print("CTRADER: APLICACION AUTENTICADA")
        print("=================================")

        status["aplicacion_autenticada"] = True

        print("CTRADER: AUTENTICANDO CUENTA")

        request_message = ProtoOAAccountAuthReq()

        request_message.ctidTraderAccountId = ACCOUNT_ID
        request_message.accessToken = ACCESS_TOKEN

        deferred = client.send(
            request_message
        )

        deferred.addCallbacks(
            account_authenticated,
            on_error
        )

    # ========================================================
    # CUENTA AUTENTICADA
    # ========================================================

    def account_authenticated(response):

        print("=================================")
        print("CTRADER: CUENTA AUTENTICADA")
        print("ACCOUNT ID:", ACCOUNT_ID)
        print("DEMO: SI")
        print("TRADING HABILITADO")
        print("=================================")

        status["cuenta_autenticada"] = True

        print("=================================")
        print("CTRADER: CLIENTE LISTO PARA OPERAR")
        print("=================================")

    # ========================================================
    # ENVIAR ORDEN
    # ========================================================

    def send_order(order):

        symbol = order["symbol"]
        side = order["side"]

        print("=================================")
        print("CTRADER: PROCESANDO ORDEN")
        print("SIMBOLO:", symbol)
        print("LADO:", side)
        print("=================================")

        if not status["conectado"]:

            print("CTRADER: NO CONECTADO")
            return

        if not status["aplicacion_autenticada"]:

            print("CTRADER: APLICACION NO AUTENTICADA")
            return

        if not status["cuenta_autenticada"]:

            print("CTRADER: CUENTA NO AUTENTICADA")
            return

        if symbol not in SYMBOLS:

            print("CTRADER: SIMBOLO NO CONFIGURADO")
            return

        symbol_id = SYMBOLS[symbol]["id"]
        volume = SYMBOLS[symbol]["volume"]

        if side == "BUY":

            trade_side = ProtoOATradeSide.BUY

        else:

            trade_side = ProtoOATradeSide.SELL

        print("SYMBOL ID:", symbol_id)
        print("VOLUMEN:", volume)
        print("LOTES:", 0.01)
        print("LADO:", side)
        print("CUENTA:", ACCOUNT_ID)

        request_message = ProtoOANewOrderReq()

        request_message.ctidTraderAccountId = ACCOUNT_ID
        request_message.symbolId = symbol_id

        request_message.orderType = (
            ProtoOAOrderType.MARKET
        )

        request_message.tradeSide = trade_side

        request_message.volume = volume

        print("=================================")
        print("CTRADER: ENVIANDO ORDEN")
        print("=================================")

        deferred = client.send(
            request_message
        )

        deferred.addCallbacks(
            order_sent,
            on_error
        )

    # ========================================================
    # RESPUESTA ORDEN
    # ========================================================

    def order_sent(response):

        print("=================================")
        print("CTRADER: RESPUESTA DE ORDEN")
        print("=================================")

        try:

            print(
                Protobuf.extract(response)
            )

        except Exception as error:

            print(
                "CTRADER: ERROR MOSTRANDO RESPUESTA"
            )

            print(error)

    # ========================================================
    # REVISAR COLA
    # ========================================================

    def check_order_queue():

        try:

            while True:

                order = order_queue.get_nowait()

                print("=================================")
                print("CTRADER: ORDEN RECIBIDA DESDE FLASK")
                print(order)
                print("=================================")

                send_order(order)

        except Exception:

            pass

    # ========================================================
    # CREAR CLIENTE
    # ========================================================

    try:

        print("CTRADER: CREANDO CLIENTE DEMO")

        client = Client(
            HOST,
            PORT,
            TcpProtocol
        )

        status["cliente_creado"] = True

        print("CTRADER: CLIENTE CREADO")

        client.setConnectedCallback(
            connected
        )

        client.setDisconnectedCallback(
            disconnected
        )

        client.setMessageReceivedCallback(
            on_message_received
        )

        print("CTRADER: CALLBACKS CONFIGURADOS")

        print("CTRADER: INICIANDO SERVICIO")

        client.startService()

        print("CTRADER: SERVICIO INICIADO")

        # Revisar la cola cada 100 ms
        queue_checker = LoopingCall(
            check_order_queue
        )

        queue_checker.start(
            0.1,
            now=False
        )

        print("=================================")
        print("CTRADER: INICIANDO REACTOR")
        print("=================================")

        reactor.run(
            installSignalHandlers=False
        )

    except Exception as error:

        print("=================================")
        print("CTRADER: ERROR GENERAL")
        print(error)
        print("=================================")


# ============================================================
# INICIAR PROCESO CTRADER
# ============================================================

ctrader_process_instance = None


def start_ctrader_process():

    global ctrader_process_instance

    print("=================================")
    print("TRADINGVIEW CTRADER")
    print("INICIANDO PROCESO CTRADER")
    print("=================================")

    ctrader_process_instance = multiprocessing.Process(
        target=ctrader_process,
        args=(
            order_queue,
            ctrader_status
        ),
        daemon=True
    )

    ctrader_process_instance.start()

    print(
        "CTRADER: PROCESO INICIADO PID:",
        ctrader_process_instance.pid
    )


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

        print(
            "Mensaje recibido:",
            message
        )

        parsed = parse_alert(
            message
        )

        if parsed is None:

            print(
                "CTRADER: ALERTA NO RECONOCIDA"
            )

            return jsonify({
                "success": False,
                "error": "alerta_no_reconocida"
            }), 400

        print("=================================")
        print(
            "CTRADER: ALERTA",
            parsed["symbol"],
            parsed["side"]
        )
        print(
            "PRECIO:",
            parsed["price"]
        )
        print("=================================")

        # -----------------------------------------
        # VERIFICAR ESTADO
        # -----------------------------------------

        print(
            "CTRADER CLIENTE CREADO:",
            ctrader_status["cliente_creado"]
        )

        print(
            "CTRADER CONECTADO:",
            ctrader_status["conectado"]
        )

        print(
            "CTRADER APLICACION AUTENTICADA:",
            ctrader_status["aplicacion_autenticada"]
        )

        print(
            "CTRADER CUENTA AUTENTICADA:",
            ctrader_status["cuenta_autenticada"]
        )

        # -----------------------------------------
        # MANDAR ORDEN A PROCESO CTRADER
        # -----------------------------------------

        if not ctrader_status["cliente_creado"]:

            print(
                "CTRADER: CLIENTE TODAVIA NO CREADO"
            )

            return jsonify({
                "success": False,
                "error": "ctrader_cliente_no_creado"
            }), 200

        if not ctrader_status["conectado"]:

            print(
                "CTRADER: TODAVIA NO CONECTADO"
            )

            return jsonify({
                "success": False,
                "error": "ctrader_no_conectado"
            }), 200

        if not ctrader_status["cuenta_autenticada"]:

            print(
                "CTRADER: CUENTA TODAVIA NO AUTENTICADA"
            )

            return jsonify({
                "success": False,
                "error": "cuenta_no_autenticada"
            }), 200

        order_queue.put({
            "symbol": parsed["symbol"],
            "side": parsed["side"],
            "price": parsed["price"]
        })

        print("=================================")
        print("CTRADER: ORDEN ENVIADA A COLA")
        print("=================================")

        return jsonify({
            "success": True,
            "message": "orden_enviada_a_ctrader",
            "alerta": parsed
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
# HOME
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return (
        "Servidor TradingView cTrader funcionando"
    )


# ============================================================
# STATUS
# ============================================================

@app.route(
    "/status",
    methods=["GET"]
)
def status():

    return jsonify({

        "cliente_creado":
            bool(
                ctrader_status["cliente_creado"]
            ),

        "conectado":
            bool(
                ctrader_status["conectado"]
            ),

        "aplicacion_autenticada":
            bool(
                ctrader_status[
                    "aplicacion_autenticada"
                ]
            ),

        "cuenta_autenticada":
            bool(
                ctrader_status[
                    "cuenta_autenticada"
                ]
            ),

        "cuenta":
            ACCOUNT_ID
    })


# ============================================================
# ARRANQUE
# ============================================================

start_ctrader_process()
