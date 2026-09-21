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

ctrader_client = None
cuenta_autenticada = False

xauusd_symbol_id = None
nasdaq_symbol_id = None


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
    global nasdaq_symbol_id
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
        print("BUSCANDO XAUUSD Y NASDAQ")
        print("================================")

        for simbolo in respuesta.symbol:

            nombre = simbolo.symbolName

            if not nombre:
                continue

            nombre_mayuscula = nombre.upper()
            nombre_limpio = nombre_mayuscula.replace("/", "")

            # ---------------------------------
            # XAUUSD
            # ---------------------------------

            if nombre_limpio == "XAUUSD":

                xauusd_symbol_id = simbolo.symbolId

                print("--------------------------------")
                print("XAUUSD ENCONTRADO")
                print("NOMBRE:", nombre)
                print("SYMBOL ID:", xauusd_symbol_id)
                print("--------------------------------")

                detalle = ProtoOASymbolByIdReq()
                detalle.ctidTraderAccountId = ACCOUNT_ID
                detalle.symbolId.append(xauusd_symbol_id)

                print("CTRADER: SOLICITANDO DATOS XAUUSD")

                client.send(detalle)

            # ---------------------------------
            # NASDAQ
            # ---------------------------------

            if (
                "NAS100" in nombre_limpio
                or "NAS100USD" in nombre_limpio
                or "USTEC" in nombre_limpio
                or "US100" in nombre_limpio
                or "NASDAQ" in nombre_limpio
            ):

                nasdaq_symbol_id = simbolo.symbolId

                print("--------------------------------")
                print("POSIBLE NASDAQ ENCONTRADO")
                print("NOMBRE:", nombre)
                print("SYMBOL ID:", nasdaq_symbol_id)
                print("--------------------------------")

                detalle = ProtoOASymbolByIdReq()
                detalle.ctidTraderAccountId = ACCOUNT_ID
                detalle.symbolId.append(nasdaq_symbol_id)

                print("CTRADER: SOLICITANDO DATOS NASDAQ")

                client.send(detalle)

        print("================================")
        print("BUSQUEDA DE SIMBOLOS TERMINADA")
        print("================================")

    # -----------------------------------------
    # DATOS COMPLETOS DEL SIMBOLO
    # -----------------------------------------

    elif message.payloadType == ProtoOASymbolByIdRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("DATOS RECIBIDOS DE SYMBOL BY ID")
        print("================================")

        for simbolo in respuesta.symbol:

            print("--------------------------------")
            print("SYMBOL ID:", simbolo.symbolId)
            print("LOT SIZE:", simbolo.lotSize)
            print("MIN VOLUME:", simbolo.minVolume)
            print("STEP VOLUME:", simbolo.stepVolume)
            print("--------------------------------")

            if simbolo.symbolId == xauusd_symbol_id:

                print("XAUUSD CONFIRMADO")
                print("SYMBOL ID:", simbolo.symbolId)
                print("LOT SIZE:", simbolo.lotSize)
                print("MIN VOLUME:", simbolo.minVolume)
                print("STEP VOLUME:", simbolo.stepVolume)

            elif simbolo.symbolId == nasdaq_symbol_id:

                print("NASDAQ CONFIRMADO")
                print("SYMBOL ID:", simbolo.symbolId)
                print("LOT SIZE:", simbolo.lotSize)
                print("MIN VOLUME:", simbolo.minVolume)
                print("STEP VOLUME:", simbolo.stepVolume)

        print("================================")
        print("NO SE ABRIRAN OPERACIONES")
        print("================================")

    # -----------------------------------------
    # OTROS MENSAJES
    # -----------------------------------------

    else:

        print("CTRADER: OTRO MENSAJE RECIBIDO")


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

    print("NO SE ABRIRAN OPERACIONES")

    return "Webhook recibido correctamente"


print("INICIANDO HILO CTRADER")

threading.Thread(
    target=iniciar_ctrader,
    daemon=True
).start()
