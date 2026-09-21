from flask import Flask, request
import os
import threading

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from twisted.internet import reactor


app = Flask(__name__)


# =========================================================
# CONFIGURACION
# =========================================================

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

# CUENTA DEMO CONFIRMADA
ACCOUNT_ID = 48481130


# =========================================================
# SIMBOLOS CONFIRMADOS
# =========================================================

NASDAQ_SYMBOL_ID = 10014
XAUUSD_SYMBOL_ID = 41


# =========================================================
# VOLUMENES
# =========================================================

# NAS100:
# Lot size = 100
# 0.01 lote = volumen 10

NASDAQ_VOLUME = 10


# XAUUSD:
# Lot size = 10000
# 0.01 lote = volumen 100

XAUUSD_VOLUME = 100


# =========================================================
# STOP LOSS / TAKE PROFIT
# =========================================================

STOP_LOSS_PIPS = 50
TAKE_PROFIT_PIPS = 100


# =========================================================
# ESTADO
# =========================================================

ctrader_client = None
cuenta_autenticada = False

nasdaq_pip_position = None
xauusd_pip_position = None

nasdaq_listo = False
xauusd_listo = False


# =========================================================
# CONEXION
# =========================================================

def conectado(client):

    print("================================")
    print("CTRADER: CONECTADO")
    print("================================")

    auth = ProtoOAApplicationAuthReq()

    auth.clientId = CLIENT_ID
    auth.clientSecret = CLIENT_SECRET

    print("CTRADER: ENVIANDO AUTENTICACION")

    client.send(auth)


def desconectado(client, reason):

    print("================================")
    print("CTRADER: DESCONECTADO")
    print("MOTIVO:", reason)
    print("================================")


# =========================================================
# MENSAJES CTRADER
# =========================================================

def mensaje_recibido(client, message):

    global ctrader_client
    global cuenta_autenticada
    global nasdaq_pip_position
    global xauusd_pip_position
    global nasdaq_listo
    global xauusd_listo

    ctrader_client = client

    print("CTRADER: MENSAJE RECIBIDO")


    # =====================================================
    # APLICACION AUTENTICADA
    # =====================================================

    if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

        print("CTRADER: APLICACION AUTENTICADA")

        cuentas = ProtoOAGetAccountListByAccessTokenReq()

        cuentas.accessToken = ACCESS_TOKEN

        print("CTRADER: SOLICITANDO CUENTAS")

        client.send(cuentas)


    # =====================================================
    # CUENTAS
    # =====================================================

    elif message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:

        respuesta = Protobuf.extract(message)

        for cuenta in respuesta.ctidTraderAccount:

            print("================================")
            print("CUENTA ENCONTRADA")
            print("ACCOUNT ID:", cuenta.ctidTraderAccountId)
            print("TRADER LOGIN:", cuenta.traderLogin)
            print("ES LIVE:", cuenta.isLive)
            print("================================")

            if cuenta.ctidTraderAccountId == ACCOUNT_ID:

                print("CUENTA DEMO CORRECTA ENCONTRADA")

                auth_cuenta = ProtoOAAccountAuthReq()

                auth_cuenta.ctidTraderAccountId = ACCOUNT_ID
                auth_cuenta.accessToken = ACCESS_TOKEN

                print("CTRADER: AUTENTICANDO CUENTA")

                client.send(auth_cuenta)


    # =====================================================
    # CUENTA AUTENTICADA
    # =====================================================

    elif message.payloadType == ProtoOAAccountAuthRes().payloadType:

        cuenta_autenticada = True

        print("================================")
        print("CUENTA CTRADER AUTENTICADA")
        print("ACCOUNT ID:", ACCOUNT_ID)
        print("================================")

        detalle = ProtoOASymbolByIdReq()

        detalle.ctidTraderAccountId = ACCOUNT_ID

        detalle.symbolId.append(NASDAQ_SYMBOL_ID)
        detalle.symbolId.append(XAUUSD_SYMBOL_ID)

        print("CTRADER: SOLICITANDO DATOS DE NAS100 Y XAUUSD")

        client.send(detalle)


    # =====================================================
    # DATOS DE LOS SIMBOLOS
    # =====================================================

    elif message.payloadType == ProtoOASymbolByIdRes().payloadType:

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

            if hasattr(simbolo, "digits"):
                print("DIGITS:", simbolo.digits)

            if hasattr(simbolo, "pipPosition"):
                print("PIP POSITION:", simbolo.pipPosition)

            print("--------------------------------")


            # ---------------------------------------------
            # NAS100
            # ---------------------------------------------

            if simbolo.symbolId == NASDAQ_SYMBOL_ID:

                if hasattr(simbolo, "pipPosition"):

                    nasdaq_pip_position = simbolo.pipPosition

                nasdaq_listo = True

                print("NAS100 CONFIRMADO")
                print("SYMBOL ID:", NASDAQ_SYMBOL_ID)
                print("VOLUMEN:", NASDAQ_VOLUME)
                print("LOTES: 0.01")
                print("PIP POSITION:", nasdaq_pip_position)


            # ---------------------------------------------
            # XAUUSD
            # ---------------------------------------------

            elif simbolo.symbolId == XAUUSD_SYMBOL_ID:

                if hasattr(simbolo, "pipPosition"):

                    xauusd_pip_position = simbolo.pipPosition

                xauusd_listo = True

                print("XAUUSD CONFIRMADO")
                print("SYMBOL ID:", XAUUSD_SYMBOL_ID)
                print("VOLUMEN:", XAUUSD_VOLUME)
                print("LOTES: 0.01")
                print("PIP POSITION:", xauusd_pip_position)


        print("================================")

        if nasdaq_listo and xauusd_listo:

            print("NAS100 Y XAUUSD LISTOS PARA OPERAR")

        else:

            print("FALTA CONFIRMAR ALGUN SIMBOLO")

        print("================================")


    # =====================================================
    # EVENTO DE EJECUCION DE ORDEN
    # =====================================================

    elif message.payloadType == ProtoOAExecutionEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: EVENTO DE EJECUCION")
        print("================================")

        print("EXECUTION TYPE:", respuesta.executionType)

        # -------------------------------------------------
        # ORDER
        # -------------------------------------------------

        if respuesta.HasField("order"):

            orden = respuesta.order

            print("ORDER ID:", orden.orderId)
            print("ORDER STATUS:", orden.orderStatus)

            if orden.HasField("executionPrice"):

                print(
                    "PRECIO DE EJECUCION:",
                    orden.executionPrice
                )

            if orden.HasField("executedVolume"):

                print(
                    "VOLUMEN EJECUTADO:",
                    orden.executedVolume
                )

            if orden.HasField("stopLoss"):

                print(
                    "STOP LOSS:",
                    orden.stopLoss
                )

            if orden.HasField("takeProfit"):

                print(
                    "TAKE PROFIT:",
                    orden.takeProfit
                )


        # -------------------------------------------------
        # POSITION
        # -------------------------------------------------

        if respuesta.HasField("position"):

            posicion = respuesta.position

            print(
                "POSITION ID:",
                posicion.positionId
            )

            if posicion.HasField("price"):

                print(
                    "PRECIO POSICION:",
                    posicion.price
                )

            if posicion.HasField("stopLoss"):

                print(
                    "SL POSICION:",
                    posicion.stopLoss
                )

            if posicion.HasField("takeProfit"):

                print(
                    "TP POSICION:",
                    posicion.takeProfit
                )


        # -------------------------------------------------
        # DEAL
        # -------------------------------------------------

        if respuesta.HasField("deal"):

            deal = respuesta.deal

            print(
                "DEAL ID:",
                deal.dealId
            )

            print(
                "POSITION ID:",
                deal.positionId
            )

            if deal.HasField("executionPrice"):

                print(
                    "PRECIO DEAL:",
                    deal.executionPrice
                )

            print(
                "DEAL STATUS:",
                deal.dealStatus
            )


        print("================================")


    # =====================================================
    # ERROR DE ORDEN
    # =====================================================

    elif message.payloadType == ProtoOAOrderErrorEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: ERROR AL ABRIR ORDEN")
        print("================================")

        print("ERROR CODE:", respuesta.errorCode)

        if respuesta.HasField("description"):

            print(
                "DESCRIPCION:",
                respuesta.description
            )

        print("================================")


    # =====================================================
    # OTROS MENSAJES
    # =====================================================

    else:

        print("CTRADER: OTRO MENSAJE RECIBIDO")


# =========================================================
# CALCULAR DISTANCIA SL / TP
# =========================================================

def calcular_distancia(pips):

    # cTrader expresa relativeStopLoss y
    # relativeTakeProfit en 1/100000
    # de unidad de precio.

    return int(round(pips * 100000))


# =========================================================
# ABRIR OPERACION
# =========================================================

def abrir_operacion(symbol_id, volume, direccion, nombre):

    global ctrader_client
    global cuenta_autenticada

    print("================================")
    print("PREPARANDO OPERACION")
    print("================================")

    print("ACTIVO:", nombre)
    print("SYMBOL ID:", symbol_id)
    print("DIRECCION:", direccion)
    print("VOLUMEN:", volume)
    print("LOTES: 0.01")


    # -----------------------------------------------------
    # CONEXION
    # -----------------------------------------------------

    if ctrader_client is None:

        print("ERROR: CTRADER NO ESTA CONECTADO")
        print("NO SE ABRE LA OPERACION")

        return


    # -----------------------------------------------------
    # CUENTA
    # -----------------------------------------------------

    if not cuenta_autenticada:

        print("ERROR: CUENTA NO AUTENTICADA")
        print("NO SE ABRE LA OPERACION")

        return


    # -----------------------------------------------------
    # SL / TP
    # -----------------------------------------------------

    relative_sl = calcular_distancia(
        STOP_LOSS_PIPS
    )

    relative_tp = calcular_distancia(
        TAKE_PROFIT_PIPS
    )


    print("STOP LOSS:", STOP_LOSS_PIPS, "PIPS")
    print("RELATIVE SL:", relative_sl)

    print("TAKE PROFIT:", TAKE_PROFIT_PIPS, "PIPS")
    print("RELATIVE TP:", relative_tp)

    print("================================")


    # -----------------------------------------------------
    # CREAR ORDEN
    # -----------------------------------------------------

    orden = ProtoOANewOrderReq()

    orden.ctidTraderAccountId = ACCOUNT_ID

    orden.symbolId = symbol_id

    orden.orderType = ProtoOAOrderType.MARKET


    # -----------------------------------------------------
    # DIRECCION
    # -----------------------------------------------------

    if direccion == "BUY":

        orden.tradeSide = ProtoOATradeSide.BUY

    elif direccion == "SELL":

        orden.tradeSide = ProtoOATradeSide.SELL

    else:

        print("ERROR: DIRECCION INVALIDA")

        return


    # -----------------------------------------------------
    # VOLUMEN
    # -----------------------------------------------------

    orden.volume = volume


    # -----------------------------------------------------
    # SL / TP RELATIVOS
    # -----------------------------------------------------

    orden.relativeStopLoss = relative_sl

    orden.relativeTakeProfit = relative_tp


    # -----------------------------------------------------
    # LABEL
    # -----------------------------------------------------

    orden.label = "TV_" + nombre


    print("================================")
    print("CTRADER: ENVIANDO ORDEN")
    print("================================")

    print("ACTIVO:", nombre)
    print("DIRECCION:", direccion)
    print("VOLUMEN:", volume)
    print("SL:", STOP_LOSS_PIPS, "PIPS")
    print("TP:", TAKE_PROFIT_PIPS, "PIPS")

    print("================================")


    try:

        ctrader_client.send(orden)

        print("CTRADER: ORDEN ENVIADA CORRECTAMENTE")

    except Exception as e:

        print("================================")
        print("ERROR ENVIANDO ORDEN")
        print("ERROR:", e)
        print("================================")


# =========================================================
# PROCESAR ALERTA
# =========================================================

def procesar_alerta(mensaje):

    texto = mensaje.upper().strip()

    print("================================")
    print("ANALIZANDO ALERTA")
    print("MENSAJE:", texto)
    print("================================")


    # =====================================================
    # IDENTIFICAR ACTIVO
    # =====================================================

    es_nasdaq = (
        "NASDAQ" in texto
        or "NAS100" in texto
    )


    es_oro = (
        "XAUUSD" in texto
        or "ORO" in texto
    )


    # =====================================================
    # IDENTIFICAR DIRECCION
    # =====================================================

    es_compra = (
        "COMPRA" in texto
        or "BUY" in texto
    )


    es_venta = (
        "VENTA" in texto
        or "SELL" in texto
    )


    # =====================================================
    # ALERTA AMBIGUA
    # =====================================================

    if es_compra and es_venta:

        print("ALERTA AMBIGUA")
        print("CONTIENE COMPRA Y VENTA")
        print("NO SE ABRE NINGUNA OPERACION")

        return


    # =====================================================
    # SIN DIRECCION
    # =====================================================

    if not es_compra and not es_venta:

        print("NO SE ENCONTRO COMPRA NI VENTA")
        print("NO SE ABRE NINGUNA OPERACION")

        return


    # =====================================================
    # NASDAQ
    # =====================================================

    if es_nasdaq:

        if es_compra:

            print("================================")
            print("ALERTA NASDAQ: COMPRA")
            print("================================")

            threading.Thread(
                target=abrir_operacion,
                args=(
                    NASDAQ_SYMBOL_ID,
                    NASDAQ_VOLUME,
                    "BUY",
                    "NAS100"
                ),
                daemon=True
            ).start()

            return


        if es_venta:

            print("================================")
            print("ALERTA NASDAQ: VENTA")
            print("================================")

            threading.Thread(
                target=abrir_operacion,
                args=(
                    NASDAQ_SYMBOL_ID,
                    NASDAQ_VOLUME,
                    "SELL",
                    "NAS100"
                ),
                daemon=True
            ).start()

            return


    # =====================================================
    # ORO
    # =====================================================

    if es_oro:

        if es_compra:

            print("================================")
            print("ALERTA XAUUSD: COMPRA")
            print("================================")

            threading.Thread(
                target=abrir_operacion,
                args=(
                    XAUUSD_SYMBOL_ID,
                    XAUUSD_VOLUME,
                    "BUY",
                    "XAUUSD"
                ),
                daemon=True
            ).start()

            return


        if es_venta:

            print("================================")
            print("ALERTA XAUUSD: VENTA")
            print("================================")

            threading.Thread(
                target=abrir_operacion,
                args=(
                    XAUUSD_SYMBOL_ID,
                    XAUUSD_VOLUME,
                    "SELL",
                    "XAUUSD"
                ),
                daemon=True
            ).start()

            return


    # =====================================================
    # ACTIVO NO RECONOCIDO
    # =====================================================

    print("ACTIVO NO RECONOCIDO")
    print("NO SE ABRE NINGUNA OPERACION")


# =========================================================
# WEBHOOK
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    mensaje = request.get_data(as_text=True).strip()

    print("================================")
    print("WEBHOOK RECIBIDO")
    print("MENSAJE RECIBIDO:", mensaje)
    print("================================")

    procesar_alerta(mensaje)

    return "Webhook recibido correctamente"


# =========================================================
# PAGINAS
# =========================================================

@app.route("/")
def home():

    return "Servidor TradingView cTrader funcionando"


@app.route("/status")
def status():

    return "OK"


# =========================================================
# INICIAR CTRADER
# =========================================================

def iniciar_ctrader():

    global ctrader_client

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


    print("CTRADER: VARIABLES ENCONTRADAS")

    print("CTRADER: CREANDO CLIENTE DEMO")


    client = Client(
        EndPoints.PROTOBUF_DEMO_HOST,
        EndPoints.PROTOBUF_PORT,
        TcpProtocol
    )


    ctrader_client = client


    print("CTRADER: CLIENTE CREADO")


    client.setConnectedCallback(conectado)

    client.setDisconnectedCallback(desconectado)

    client.setMessageReceivedCallback(mensaje_recibido)


    print("CTRADER: CALLBACKS CONFIGURADOS")

    print("CTRADER: INICIANDO SERVICIO")


    client.startService()


    print("CTRADER: SERVICIO INICIADO")


    reactor.run(installSignalHandlers=False)


# =========================================================
# INICIAR HILO CTRADER
# =========================================================

print("INICIANDO HILO CTRADER")


threading.Thread(
    target=iniciar_ctrader,
    daemon=True
).start()
