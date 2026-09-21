from flask import Flask, request
import threading
import time

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from ctrader_open_api.messages.OpenApiCommonModelMessages_pb2 import *

from twisted.internet import reactor
from twisted.internet.task import LoopingCall


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIGURACION
# ============================================================

CTRADER_CLIENT_ID = "TU_CLIENT_ID"
CTRADER_CLIENT_SECRET = "TU_CLIENT_SECRET"

CTRADER_ACCESS_TOKEN = "TU_ACCESS_TOKEN"

ACCOUNT_ID = 48481130

NASDAQ_SYMBOL_ID = 10014
XAUUSD_SYMBOL_ID = 41

NASDAQ_VOLUME = 10       # 0.01 lote
XAUUSD_VOLUME = 100      # 0.01 lote

STOP_LOSS_PIPS = 50
TAKE_PROFIT_PIPS = 100


# ============================================================
# CLIENTE CTRADER
# ============================================================

ctrader_client = None
heartbeat_loop = None
conectado = False
cuenta_autenticada = False
simbolos_listos = False


# ============================================================
# CALCULO SL / TP
# ============================================================

def calcular_distancia(pips):
    return int(round(pips * 100000))


# ============================================================
# HEARTBEAT
# ============================================================

def enviar_heartbeat():
    global ctrader_client

    try:
        if ctrader_client is not None:
            heartbeat = ProtoHeartbeatEvent()
            ctrader_client.send(heartbeat)
            print("CTRADER: HEARTBEAT ENVIADO")

    except Exception as e:
        print("CTRADER: ERROR EN HEARTBEAT:", e)


def iniciar_heartbeat():

    global heartbeat_loop

    try:

        if heartbeat_loop is not None:
            return

        print("CTRADER: INICIANDO HEARTBEAT")

        heartbeat_loop = LoopingCall(enviar_heartbeat)

        # Cada 5 segundos para mantener la conexion viva
        heartbeat_loop.start(5.0, now=False)

    except Exception as e:
        print("CTRADER: ERROR INICIANDO HEARTBEAT:", e)


# ============================================================
# ABRIR OPERACION
# ============================================================

def abrir_operacion(symbol_id, volume, lado, nombre):

    global ctrader_client
    global simbolos_listos

    if ctrader_client is None:
        print("CTRADER: CLIENTE NO DISPONIBLE")
        return

    if not simbolos_listos:
        print("CTRADER: LOS SIMBOLOS TODAVIA NO ESTAN LISTOS")
        return

    try:

        orden = ProtoOANewOrderReq()

        orden.ctidTraderAccountId = ACCOUNT_ID
        orden.symbolId = symbol_id
        orden.orderType = ProtoOAOrderType.MARKET

        if lado == "BUY":
            orden.tradeSide = ProtoOATradeSide.BUY
        else:
            orden.tradeSide = ProtoOATradeSide.SELL

        orden.volume = volume

        orden.relativeStopLoss = calcular_distancia(STOP_LOSS_PIPS)
        orden.relativeTakeProfit = calcular_distancia(TAKE_PROFIT_PIPS)

        orden.label = "TV_" + nombre

        print("================================")
        print("CTRADER: ENVIANDO ORDEN")
        print("SIMBOLO:", nombre)
        print("SYMBOL ID:", symbol_id)
        print("LADO:", lado)
        print("VOLUMEN:", volume)
        print("SL:", STOP_LOSS_PIPS, "PIPS")
        print("TP:", TAKE_PROFIT_PIPS, "PIPS")
        print("================================")

        ctrader_client.send(orden)

    except Exception as e:

        print("CTRADER: ERROR AL ENVIAR ORDEN")
        print(e)


# ============================================================
# PROCESAR ALERTA DE TRADINGVIEW
# ============================================================

def procesar_alerta(mensaje):

    mensaje = mensaje.upper().strip()

    print("================================")
    print("CTRADER: PROCESANDO ALERTA")
    print("MENSAJE:", mensaje)
    print("================================")

    es_compra = (
        "COMPRA" in mensaje or
        "BUY" in mensaje
    )

    es_venta = (
        "VENTA" in mensaje or
        "SELL" in mensaje
    )

    es_nasdaq = (
        "NASDAQ" in mensaje or
        "NAS100" in mensaje
    )

    es_oro = (
        "XAUUSD" in mensaje or
        "ORO" in mensaje
    )

    # Evitar mensaje ambiguo
    if es_compra and es_venta:

        print("CTRADER: ALERTA AMBIGUA")
        print("NO SE ENVIA ORDEN")
        return

    # ========================================================
    # NASDAQ
    # ========================================================

    if es_nasdaq:

        if es_compra:

            abrir_operacion(
                NASDAQ_SYMBOL_ID,
                NASDAQ_VOLUME,
                "BUY",
                "NAS100"
            )

        elif es_venta:

            abrir_operacion(
                NASDAQ_SYMBOL_ID,
                NASDAQ_VOLUME,
                "SELL",
                "NAS100"
            )

        else:

            print("CTRADER: ALERTA NASDAQ SIN COMPRA/VENTA")

        return

    # ========================================================
    # XAUUSD
    # ========================================================

    if es_oro:

        if es_compra:

            abrir_operacion(
                XAUUSD_SYMBOL_ID,
                XAUUSD_VOLUME,
                "BUY",
                "XAUUSD"
            )

        elif es_venta:

            abrir_operacion(
                XAUUSD_SYMBOL_ID,
                XAUUSD_VOLUME,
                "SELL",
                "XAUUSD"
            )

        else:

            print("CTRADER: ALERTA XAUUSD SIN COMPRA/VENTA")

        return

    print("CTRADER: SIMBOLO NO RECONOCIDO")


# ============================================================
# WEBHOOK
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    mensaje = request.get_data(as_text=True)

    print("================================")
    print("WEBHOOK RECIBIDO")
    print("Mensaje recibido:", mensaje)
    print("================================")

    procesar_alerta(mensaje)

    return "Webhook recibido correctamente", 200


# ============================================================
# PAGINA PRINCIPAL
# ============================================================

@app.route("/")
def home():

    return "Servidor TradingView cTrader funcionando"


@app.route("/status")
def status():

    return "OK"


# ============================================================
# MENSAJES CTRADER
# ============================================================

def mensaje_recibido(client, message):

    global cuenta_autenticada
    global simbolos_listos

    print("CTRADER: MENSAJE RECIBIDO")

    # --------------------------------------------------------
    # HEARTBEAT
    # --------------------------------------------------------

    if message.payloadType == ProtoHeartbeatEvent().payloadType:

        return

    # --------------------------------------------------------
    # AUTENTICACION DE APLICACION
    # --------------------------------------------------------

    if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

        print("CTRADER: APLICACION AUTENTICADA")

        request = ProtoOATraderReq()

        request.ctidTraderAccountId = ACCOUNT_ID

        client.send(request)

        return

    # --------------------------------------------------------
    # CUENTAS
    # --------------------------------------------------------

    if message.payloadType == ProtoOATraderRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CUENTA ENCONTRADA")
        print("ACCOUNT ID:", respuesta.trader.ctidTraderAccountId)
        print("TRADER LOGIN:", respuesta.trader.login)
        print("================================")

        if respuesta.trader.ctidTraderAccountId == ACCOUNT_ID:

            print("CUENTA DEMO CORRECTA ENCONTRADA")

            auth = ProtoOAAccountAuthReq()

            auth.ctidTraderAccountId = ACCOUNT_ID
            auth.accessToken = CTRADER_ACCESS_TOKEN

            print("CTRADER: AUTENTICANDO CUENTA")

            client.send(auth)

        return

    # --------------------------------------------------------
    # CUENTA AUTENTICADA
    # --------------------------------------------------------

    if message.payloadType == ProtoOAAccountAuthRes().payloadType:

        cuenta_autenticada = True

        print("================================")
        print("CUENTA CTRADER AUTENTICADA")
        print("ACCOUNT ID:", ACCOUNT_ID)
        print("================================")

        print("NAS100 ID:", NASDAQ_SYMBOL_ID)
        print("XAUUSD ID:", XAUUSD_SYMBOL_ID)

        # Solicitar NAS100
        req_nasdaq = ProtoOASymbolByIdReq()

        req_nasdaq.ctidTraderAccountId = ACCOUNT_ID
        req_nasdaq.symbolId.append(NASDAQ_SYMBOL_ID)

        # Solicitar XAUUSD
        req_oro = ProtoOASymbolByIdReq()

        req_oro.ctidTraderAccountId = ACCOUNT_ID
        req_oro.symbolId.append(XAUUSD_SYMBOL_ID)

        print("CTRADER: SOLICITANDO DATOS DE NAS100 Y XAUUSD")

        client.send(req_nasdaq)
        client.send(req_oro)

        # Iniciar heartbeat
        iniciar_heartbeat()

        return

    # --------------------------------------------------------
    # DATOS DE SIMBOLO
    # --------------------------------------------------------

    if message.payloadType == ProtoOASymbolByIdRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("DATOS DE LOS SIMBOLOS")
        print("================================")

        for simbolo in respuesta.symbol:

            print("--------------------------------")
            print("SYMBOL ID:", simbolo.symbolId)
            print("LOT SIZE:", simbolo.lotSize)
            print("MIN VOLUME:", simbolo.minVolume)
            print("STEP VOLUME:", simbolo.stepVolume)
            print("DIGITS:", simbolo.digits)
            print("PIP POSITION:", simbolo.pipPosition)

            if simbolo.symbolId == NASDAQ_SYMBOL_ID:

                print("--------------------------------")
                print("NAS100 CONFIRMADO")
                print("SYMBOL ID:", simbolo.symbolId)
                print("VOLUMEN:", NASDAQ_VOLUME)
                print("LOTES: 0.01")
                print("PIP POSITION:", simbolo.pipPosition)

            if simbolo.symbolId == XAUUSD_SYMBOL_ID:

                print("--------------------------------")
                print("XAUUSD CONFIRMADO")
                print("SYMBOL ID:", simbolo.symbolId)
                print("VOLUMEN:", XAUUSD_VOLUME)
                print("LOTES: 0.01")
                print("PIP POSITION:", simbolo.pipPosition)

        simbolos_listos = True

        print("================================")
        print("NAS100 Y XAUUSD LISTOS PARA OPERAR")
        print("================================")

        return

    # --------------------------------------------------------
    # EJECUCION DE ORDEN
    # --------------------------------------------------------

    if message.payloadType == ProtoOAExecutionEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: EVENTO DE EJECUCION")
        print("EXECUTION TYPE:", respuesta.executionType)

        if respuesta.HasField("order"):

            orden = respuesta.order

            print("ORDER ID:", orden.orderId)
            print("ORDER STATUS:", orden.orderStatus)

        if respuesta.HasField("position"):

            posicion = respuesta.position

            print("POSITION ID:", posicion.positionId)

        if respuesta.HasField("deal"):

            deal = respuesta.deal

            print("DEAL ID:", deal.dealId)

        print("================================")

        return

    # --------------------------------------------------------
    # ERROR DE ORDEN
    # --------------------------------------------------------

    if message.payloadType == ProtoOAOrderErrorEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: ERROR DE ORDEN")
        print("ERROR CODE:", respuesta.errorCode)
        print("DESCRIPTION:", respuesta.description)
        print("================================")

        return


# ============================================================
# CONEXION
# ============================================================

def conectado_callback(client):

    global conectado
    global ctrader_client

    ctrader_client = client
    conectado = True

    print("================================")
    print("CTRADER: CONECTADO")
    print("================================")

    request = ProtoOAApplicationAuthReq()

    request.clientId = CTRADER_CLIENT_ID
    request.clientSecret = CTRADER_CLIENT_SECRET

    print("CTRADER: ENVIANDO AUTENTICACION")

    client.send(request)


def desconectado_callback(client, reason):

    global conectado
    global cuenta_autenticada
    global simbolos_listos

    conectado = False
    cuenta_autenticada = False
    simbolos_listos = False

    print("================================")
    print("CTRADER: DESCONECTADO")
    print("MOTIVO:", reason)
    print("================================")


# ============================================================
# INICIAR CTRADER
# ============================================================

def iniciar_ctrader():

    global ctrader_client

    while True:

        try:

            print("================================")
            print("INICIANDO CONEXION CTRADER DEMO")
            print("================================")

            ctrader_client = Client(
                EndPoints.PROTOBUF_DEMO_HOST,
                EndPoints.PROTOBUF_PORT,
                TcpProtocol
            )

            ctrader_client.setConnectedCallback(conectado_callback)
            ctrader_client.setDisconnectedCallback(desconectado_callback)
            ctrader_client.setMessageReceivedCallback(mensaje_recibido)

            ctrader_client.startService()

            reactor.run()

        except Exception as e:

            print("CTRADER: ERROR EN CONEXION")
            print(e)

        print("CTRADER: REINTENTANDO EN 10 SEGUNDOS")

        time.sleep(10)


# ============================================================
# INICIAR HILO CTRADER
# ============================================================

threading.Thread(
    target=iniciar_ctrader,
    daemon=True
).start()
