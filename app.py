import os
import threading

from flask import Flask, request

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
# VARIABLES DE ENTORNO
# ============================================================

CTRADER_CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CTRADER_CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
CTRADER_ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")


# ============================================================
# CUENTA DEMO
# ============================================================

ACCOUNT_ID = 48481130


# ============================================================
# SIMBOLOS CONFIRMADOS
# ============================================================

NASDAQ_SYMBOL_ID = 10014
XAUUSD_SYMBOL_ID = 41


# ============================================================
# VOLUMENES
# ============================================================

# NAS100:
# lot size = 100
# 0.01 lote = volumen 10

NASDAQ_VOLUME = 10


# XAUUSD:
# lot size = 10000
# 0.01 lote = volumen 100

XAUUSD_VOLUME = 100


# ============================================================
# SL / TP
# ============================================================

STOP_LOSS_PIPS = 50
TAKE_PROFIT_PIPS = 100


# ============================================================
# ESTADO CTRADER
# ============================================================

ctrader_client = None

conectado = False
aplicacion_autenticada = False
cuenta_autenticada = False

heartbeat_loop = None


# ============================================================
# ESTADO DE SIMBOLOS
# ============================================================

nas100_confirmado = False
xauusd_confirmado = False


# ============================================================
# CALCULO DE DISTANCIA
# ============================================================

def calcular_distancia(pips):
    return int(round(pips * 100000))


# ============================================================
# HEARTBEAT
# ============================================================

def enviar_heartbeat():

    global ctrader_client

    try:

        if ctrader_client is not None and conectado:

            heartbeat = ProtoHeartbeatEvent()

            ctrader_client.send(heartbeat)

            print("CTRADER: HEARTBEAT ENVIADO")

    except Exception as e:

        print("CTRADER: ERROR EN HEARTBEAT:", e)


def iniciar_heartbeat():

    global heartbeat_loop

    try:

        if heartbeat_loop is None:

            print("CTRADER: INICIANDO HEARTBEAT")

            heartbeat_loop = LoopingCall(enviar_heartbeat)

            heartbeat_loop.start(5.0, now=False)

    except Exception as e:

        print("CTRADER: ERROR INICIANDO HEARTBEAT:", e)


# ============================================================
# ABRIR OPERACION
# ============================================================

def abrir_operacion(symbol_id, volume, lado, nombre):

    global ctrader_client
    global cuenta_autenticada

    print("================================")
    print("CTRADER: PREPARANDO ORDEN")
    print("SIMBOLO:", nombre)
    print("SYMBOL ID:", symbol_id)
    print("LADO:", lado)
    print("VOLUMEN:", volume)
    print("================================")

    # --------------------------------------------------------
    # VERIFICAR CONEXION
    # --------------------------------------------------------

    if ctrader_client is None:

        print("CTRADER: CLIENTE NO DISPONIBLE")

        return

    # --------------------------------------------------------
    # VERIFICAR CUENTA
    # --------------------------------------------------------

    if not cuenta_autenticada:

        print("CTRADER: CUENTA TODAVIA NO AUTENTICADA")
        print("NO SE ENVIA LA ORDEN")

        return

    # --------------------------------------------------------
    # CREAR ORDEN
    # --------------------------------------------------------

    try:

        orden = ProtoOANewOrderReq()

        orden.ctidTraderAccountId = ACCOUNT_ID

        orden.symbolId = symbol_id

        orden.orderType = ProtoOAOrderType.MARKET

        if lado == "BUY":

            orden.tradeSide = ProtoOATradeSide.BUY

        elif lado == "SELL":

            orden.tradeSide = ProtoOATradeSide.SELL

        else:

            print("CTRADER: LADO INVALIDO")

            return

        orden.volume = volume

        orden.relativeStopLoss = calcular_distancia(
            STOP_LOSS_PIPS
        )

        orden.relativeTakeProfit = calcular_distancia(
            TAKE_PROFIT_PIPS
        )

        orden.label = "TV_" + nombre

        print("================================")
        print("CTRADER: ENVIANDO ORDEN")
        print("SIMBOLO:", nombre)
        print("SYMBOL ID:", symbol_id)
        print("LADO:", lado)
        print("VOLUMEN:", volume)
        print("SL:", STOP_LOSS_PIPS, "PIPS")
        print("TP:", TAKE_PROFIT_PIPS, "PIPS")
        print("LABEL:", orden.label)
        print("================================")

        ctrader_client.send(orden)

    except Exception as e:

        print("================================")
        print("CTRADER: ERROR AL ENVIAR ORDEN")
        print(e)
        print("================================")


# ============================================================
# PROCESAR ALERTA
# ============================================================

def procesar_alerta(mensaje):

    mensaje = mensaje.upper().strip()

    print("================================")
    print("CTRADER: PROCESANDO ALERTA")
    print("MENSAJE:", mensaje)
    print("================================")


    # ========================================================
    # DIRECCION
    # ========================================================

    es_compra = (
        "COMPRA" in mensaje
        or "BUY" in mensaje
    )

    es_venta = (
        "VENTA" in mensaje
        or "SELL" in mensaje
    )


    # ========================================================
    # EVITAR ALERTAS AMBIGUAS
    # ========================================================

    if es_compra and es_venta:

        print("CTRADER: ALERTA AMBIGUA")

        print("NO SE ENVIA ORDEN")

        return


    # ========================================================
    # NASDAQ
    # ========================================================

    es_nasdaq = (
        "NASDAQ" in mensaje
        or "NAS100" in mensaje
    )


    if es_nasdaq:

        if es_compra:

            print("CTRADER: ALERTA COMPRA NASDAQ")

            abrir_operacion(
                NASDAQ_SYMBOL_ID,
                NASDAQ_VOLUME,
                "BUY",
                "NAS100"
            )

            return


        if es_venta:

            print("CTRADER: ALERTA VENTA NASDAQ")

            abrir_operacion(
                NASDAQ_SYMBOL_ID,
                NASDAQ_VOLUME,
                "SELL",
                "NAS100"
            )

            return


        print("CTRADER: NASDAQ SIN DIRECCION")

        return


    # ========================================================
    # XAUUSD
    # ========================================================

    es_xauusd = (
        "XAUUSD" in mensaje
        or "ORO" in mensaje
    )


    if es_xauusd:

        if es_compra:

            print("CTRADER: ALERTA COMPRA XAUUSD")

            abrir_operacion(
                XAUUSD_SYMBOL_ID,
                XAUUSD_VOLUME,
                "BUY",
                "XAUUSD"
            )

            return


        if es_venta:

            print("CTRADER: ALERTA VENTA XAUUSD")

            abrir_operacion(
                XAUUSD_SYMBOL_ID,
                XAUUSD_VOLUME,
                "SELL",
                "XAUUSD"
            )

            return


        print("CTRADER: XAUUSD SIN DIRECCION")

        return


    # ========================================================
    # SIMBOLO NO RECONOCIDO
    # ========================================================

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


# ============================================================
# STATUS
# ============================================================

@app.route("/status")
def status():

    return "OK"


# ============================================================
# MENSAJES CTRADER
# ============================================================

def mensaje_recibido(client, message):

    global aplicacion_autenticada
    global cuenta_autenticada
    global nas100_confirmado
    global xauusd_confirmado

    print("CTRADER: MENSAJE RECIBIDO")


    # ========================================================
    # HEARTBEAT
    # ========================================================

    if message.payloadType == ProtoHeartbeatEvent().payloadType:

        return


    # ========================================================
    # AUTENTICACION DE APLICACION
    # ========================================================

    if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

        aplicacion_autenticada = True

        print("CTRADER: APLICACION AUTENTICADA")

        request = ProtoOATraderReq()

        request.ctidTraderAccountId = ACCOUNT_ID

        print("CTRADER: SOLICITANDO CUENTAS")

        client.send(request)

        return


    # ========================================================
    # CUENTA ENCONTRADA
    # ========================================================

    if message.payloadType == ProtoOATraderRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CUENTA ENCONTRADA")
        print("ACCOUNT ID:",
              respuesta.trader.ctidTraderAccountId)

        print("TRADER LOGIN:",
              respuesta.trader.login)

        print("================================")


        if respuesta.trader.ctidTraderAccountId != ACCOUNT_ID:

            print("CTRADER: CUENTA NO COINCIDE")

            return


        print("CUENTA DEMO CORRECTA ENCONTRADA")


        auth = ProtoOAAccountAuthReq()

        auth.ctidTraderAccountId = ACCOUNT_ID

        auth.accessToken = CTRADER_ACCESS_TOKEN

        print("CTRADER: AUTENTICANDO CUENTA")

        client.send(auth)

        return


    # ========================================================
    # CUENTA AUTENTICADA
    # ========================================================

    if message.payloadType == ProtoOAAccountAuthRes().payloadType:

        cuenta_autenticada = True

        print("================================")
        print("CUENTA CTRADER AUTENTICADA")
        print("ACCOUNT ID:", ACCOUNT_ID)
        print("================================")

        print("NAS100 ID:", NASDAQ_SYMBOL_ID)
        print("XAUUSD ID:", XAUUSD_SYMBOL_ID)

        # ----------------------------------------------------
        # SOLICITAR NAS100
        # ----------------------------------------------------

        req_nasdaq = ProtoOASymbolByIdReq()

        req_nasdaq.ctidTraderAccountId = ACCOUNT_ID

        req_nasdaq.symbolId.append(
            NASDAQ_SYMBOL_ID
        )


        # ----------------------------------------------------
        # SOLICITAR XAUUSD
        # ----------------------------------------------------

        req_xauusd = ProtoOASymbolByIdReq()

        req_xauusd.ctidTraderAccountId = ACCOUNT_ID

        req_xauusd.symbolId.append(
            XAUUSD_SYMBOL_ID
        )


        print(
            "CTRADER: SOLICITANDO DATOS DE NAS100 Y XAUUSD"
        )

        client.send(req_nasdaq)

        client.send(req_xauusd)


        # ----------------------------------------------------
        # HEARTBEAT
        # ----------------------------------------------------

        iniciar_heartbeat()

        return


    # ========================================================
    # DATOS DE SIMBOLOS
    # ========================================================

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


            # ------------------------------------------------
            # NAS100
            # ------------------------------------------------

            if simbolo.symbolId == NASDAQ_SYMBOL_ID:

                nas100_confirmado = True

                print("--------------------------------")
                print("NAS100 CONFIRMADO")
                print("SYMBOL ID:", simbolo.symbolId)
                print("VOLUMEN:", NASDAQ_VOLUME)
                print("LOTES: 0.01")
                print("PIP POSITION:", simbolo.pipPosition)


            # ------------------------------------------------
            # XAUUSD
            # ------------------------------------------------

            if simbolo.symbolId == XAUUSD_SYMBOL_ID:

                xauusd_confirmado = True

                print("--------------------------------")
                print("XAUUSD CONFIRMADO")
                print("SYMBOL ID:", simbolo.symbolId)
                print("VOLUMEN:", XAUUSD_VOLUME)
                print("LOTES: 0.01")
                print("PIP POSITION:", simbolo.pipPosition)


        if nas100_confirmado and xauusd_confirmado:

            print("================================")
            print("NAS100 Y XAUUSD LISTOS PARA OPERAR")
            print("================================")


        return


    # ========================================================
    # EJECUCION DE ORDEN
    # ========================================================

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

            print("POSITION ID:",
                  posicion.positionId)


        if respuesta.HasField("deal"):

            deal = respuesta.deal

            print("DEAL ID:",
                  deal.dealId)


        print("================================")

        return


    # ========================================================
    # ERROR DE ORDEN
    # ========================================================

    if message.payloadType == ProtoOAOrderErrorEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: ERROR DE ORDEN")
        print("ERROR CODE:", respuesta.errorCode)
        print("DESCRIPTION:", respuesta.description)
        print("================================")

        return


    # ========================================================
    # OTROS MENSAJES
    # ========================================================

    print("CTRADER: OTRO MENSAJE RECIBIDO")


# ============================================================
# CONECTADO
# ============================================================

def conectado_callback(client):

    global ctrader_client
    global conectado

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


# ============================================================
# DESCONECTADO
# ============================================================

def desconectado_callback(client, reason):

    global conectado
    global cuenta_autenticada

    conectado = False

    cuenta_autenticada = False

    print("================================")
    print("CTRADER: DESCONECTADO")
    print("MOTIVO:", reason)
    print("================================")


# ============================================================
# INICIAR CTRADER
# ============================================================

def iniciar_ctrader():

    global ctrader_client

    print("================================")
    print("INICIANDO CTRADER")
    print("================================")


    # --------------------------------------------------------
    # COMPROBAR VARIABLES
    # --------------------------------------------------------

    if not CTRADER_CLIENT_ID:

        print("CTRADER: FALTA CTRADER_CLIENT_ID")

        return


    if not CTRADER_CLIENT_SECRET:

        print("CTRADER: FALTA CTRADER_CLIENT_SECRET")

        return


    if not CTRADER_ACCESS_TOKEN:

        print("CTRADER: FALTA CTRADER_ACCESS_TOKEN")

        return


    print("CTRADER: VARIABLES ENCONTRADAS")

    print("CTRADER: CREANDO CLIENTE DEMO")


    # --------------------------------------------------------
    # CLIENTE DEMO
    # --------------------------------------------------------

    ctrader_client = Client(
        EndPoints.PROTOBUF_DEMO_HOST,
        EndPoints.PROTOBUF_PORT,
        TcpProtocol
    )


    print("CTRADER: CLIENTE CREADO")


    # --------------------------------------------------------
    # CALLBACKS
    # --------------------------------------------------------

    ctrader_client.setConnectedCallback(
        conectado_callback
    )

    ctrader_client.setDisconnectedCallback(
        desconectado_callback
    )

    ctrader_client.setMessageReceivedCallback(
        mensaje_recibido
    )


    print("CTRADER: CALLBACKS CONFIGURADOS")


    # --------------------------------------------------------
    # SERVICIO
    # --------------------------------------------------------

    print("CTRADER: INICIANDO SERVICIO")

    ctrader_client.startService()

    print("CTRADER: SERVICIO INICIADO")


    # --------------------------------------------------------
    # REACTOR
    # --------------------------------------------------------

    reactor.run()


# ============================================================
# INICIAR CTRADER EN SEGUNDO PLANO
# ============================================================

threading.Thread(
    target=iniciar_ctrader,
    daemon=True
).start()
