from flask import Flask, request
import os
import threading

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from twisted.internet import reactor


app = Flask(__name__)

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

ACCOUNT_ID = 48481130

SYMBOL_NAME = "XAUUSD"
VOLUME_LOTS = 0.01

ctrader_client = None
cuenta_autenticada = False

xauusd_symbol_id = None
xauusd_lot_size = None
xauusd_min_volume = None
xauusd_step_volume = None


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


def mensaje_recibido(client, message):
    global cuenta_autenticada
    global xauusd_symbol_id
    global xauusd_lot_size
    global xauusd_min_volume
    global xauusd_step_volume
    global ctrader_client

    ctrader_client = client

    print("CTRADER: MENSAJE RECIBIDO")

    # -----------------------------------------
    # AUTENTICACION DE LA APLICACION
    # -----------------------------------------

    if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

        print("CTRADER: APLICACION AUTENTICADA")

        cuentas = ProtoOAGetAccountListByAccessTokenReq()
        cuentas.accessToken = ACCESS_TOKEN

        print("CTRADER: SOLICITANDO CUENTAS")

        client.send(cuentas)

    # -----------------------------------------
    # LISTA DE CUENTAS
    # -----------------------------------------

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

                print("CUENTA CORRECTA ENCONTRADA")
                print("ACCOUNT ID:", ACCOUNT_ID)
                print("TRADER LOGIN:", cuenta.traderLogin)

                auth_cuenta = ProtoOAAccountAuthReq()
                auth_cuenta.ctidTraderAccountId = ACCOUNT_ID
                auth_cuenta.accessToken = ACCESS_TOKEN

                print("CTRADER: AUTENTICANDO CUENTA")

                client.send(auth_cuenta)

    # -----------------------------------------
    # CUENTA AUTENTICADA
    # -----------------------------------------

    elif message.payloadType == ProtoOAAccountAuthRes().payloadType:

        cuenta_autenticada = True

        print("================================")
        print("CUENTA CTRADER AUTENTICADA")
        print("ACCOUNT ID:", ACCOUNT_ID)
        print("================================")

        simbolos = ProtoOASymbolsListReq()
        simbolos.ctidTraderAccountId = ACCOUNT_ID
        simbolos.includeArchivedSymbols = False

        print("CTRADER: SOLICITANDO SIMBOLOS")

        client.send(simbolos)

    # -----------------------------------------
    # LISTA DE SIMBOLOS
    # -----------------------------------------

    elif message.payloadType == ProtoOASymbolsListRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("BUSCANDO XAUUSD")
        print("================================")

        encontrado = False

        for simbolo in respuesta.symbol:

            nombre = simbolo.symbolName

            if nombre and nombre.upper().replace("/", "") == "XAUUSD":

                encontrado = True

                xauusd_symbol_id = simbolo.symbolId

                print("XAUUSD ENCONTRADO")
                print("NOMBRE:", nombre)
                print("SYMBOL ID:", xauusd_symbol_id)

                detalle = ProtoOASymbolByIdReq()
                detalle.ctidTraderAccountId = ACCOUNT_ID
                detalle.symbolId.append(xauusd_symbol_id)

                print("CTRADER: SOLICITANDO DATOS COMPLETOS DE XAUUSD")

                client.send(detalle)

                break

        if not encontrado:

            print("================================")
            print("ERROR: NO SE ENCONTRO XAUUSD")
            print("================================")

    # -----------------------------------------
    # DATOS COMPLETOS DEL SIMBOLO
    # -----------------------------------------

    elif message.payloadType == ProtoOASymbolByIdRes().payloadType:

        respuesta = Protobuf.extract(message)

        for simbolo in respuesta.symbol:

            if simbolo.symbolId == xauusd_symbol_id:

                xauusd_lot_size = simbolo.lotSize
                xauusd_min_volume = simbolo.minVolume
                xauusd_step_volume = simbolo.stepVolume

                print("================================")
                print("DATOS COMPLETOS XAUUSD")
                print("================================")

                print("SYMBOL ID:", simbolo.symbolId)
                print("LOT SIZE:", xauusd_lot_size)
                print("MIN VOLUME:", xauusd_min_volume)
                print("STEP VOLUME:", xauusd_step_volume)

                print("================================")
                print("XAUUSD LISTO PARA PRUEBA DEMO")
                print("================================")

                print("LA ORDEN SOLO SE ENVIARA AL RECIBIR:")
                print("PRUEBA XAUUSD")

    # -----------------------------------------
    # EVENTO DE EJECUCION
    # -----------------------------------------

    elif message.payloadType == ProtoOAExecutionEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("EVENTO DE EJECUCION CTRADER")
        print("EXECUTION TYPE:", respuesta.executionType)
        print("================================")

        if respuesta.HasField("position"):
            print("POSITION ID:", respuesta.position.positionId)

        if respuesta.HasField("order"):
            print("ORDER ID:", respuesta.order.orderId)

        if respuesta.HasField("deal"):
            print("DEAL ID:", respuesta.deal.dealId)

    # -----------------------------------------
    # ERROR DE ORDEN
    # -----------------------------------------

    elif message.payloadType == ProtoOAOrderErrorEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("ERROR DE ORDEN CTRADER")
        print("ERROR CODE:", respuesta.errorCode)

        if respuesta.HasField("description"):
            print("DESCRIPCION:", respuesta.description)

        print("================================")

    else:

        print("CTRADER: OTRO MENSAJE RECIBIDO")


def enviar_orden_xauusd():

    global xauusd_symbol_id
    global xauusd_lot_size
    global xauusd_min_volume
    global xauusd_step_volume

    if not cuenta_autenticada:

        print("ERROR: LA CUENTA CTRADER NO ESTA AUTENTICADA")
        return

    if xauusd_symbol_id is None:

        print("ERROR: XAUUSD TODAVIA NO TIENE SYMBOL ID")
        return

    if xauusd_lot_size is None:

        print("ERROR: NO SE CONOCE EL LOT SIZE DE XAUUSD")
        return

    volumen = int(round(xauusd_lot_size * VOLUME_LOTS))

    print("================================")
    print("PREPARANDO ORDEN DEMO")
    print("================================")

    print("SIMBOLO:", SYMBOL_NAME)
    print("SYMBOL ID:", xauusd_symbol_id)
    print("LOTES:", VOLUME_LOTS)
    print("VOLUMEN PROTOCOLO:", volumen)
    print("MIN VOLUME:", xauusd_min_volume)
    print("STEP VOLUME:", xauusd_step_volume)

    if xauusd_min_volume is not None:

        if volumen < xauusd_min_volume:

            print("ERROR: EL VOLUMEN ES MENOR AL MINIMO PERMITIDO")
            return

    if xauusd_step_volume is not None:

        if volumen % xauusd_step_volume != 0:

            print("ERROR: EL VOLUMEN NO RESPETA EL STEP DEL SIMBOLO")
            return

    orden = ProtoOANewOrderReq()

    orden.ctidTraderAccountId = ACCOUNT_ID
    orden.symbolId = xauusd_symbol_id
    orden.orderType = ProtoOAOrderType.MARKET
    orden.tradeSide = ProtoOATradeSide.SELL
    orden.volume = volumen
    orden.label = "PRUEBA_XAUUSD"
    orden.comment = "Primera prueba DEMO TradingView"

    print("================================")
    print("ENVIANDO ORDEN SELL XAUUSD")
    print("================================")

    ctrader_client.send(orden)


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


@app.route("/")
def home():

    return "Servidor funcionando correctamente"


@app.route("/status")
def status():

    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():

    mensaje = request.get_data(as_text=True).strip()

    print("================================")
    print("WEBHOOK RECIBIDO")
    print("Mensaje recibido:", mensaje)
    print("================================")

    if mensaje.upper() == "PRUEBA XAUUSD":

        print("================================")
        print("SEÑAL DE PRUEBA DETECTADA")
        print("XAUUSD SELL 0.01 LOT")
        print("================================")

        threading.Thread(
            target=enviar_orden_xauusd,
            daemon=True
        ).start()

    return "Webhook recibido correctamente"


print("INICIANDO HILO CTRADER")

threading.Thread(
    target=iniciar_ctrader,
    daemon=True
).start()
