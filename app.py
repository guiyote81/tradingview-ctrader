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
    print("CTRADER: MENSAJE RECIBIDO")

    if message.payloadType == ProtoOAApplicationAuthRes().payloadType:
        print("CTRADER: APLICACION AUTENTICADA")

        cuentas = ProtoOAGetAccountListByAccessTokenReq()
        cuentas.accessToken = ACCESS_TOKEN

        print("CTRADER: SOLICITANDO TODAS LAS CUENTAS")

        client.send(cuentas)

    elif message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:
        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: CUENTAS RECIBIDAS")
        print("CANTIDAD DE CUENTAS:", len(respuesta.ctidTraderAccount))
        print("================================")

        for cuenta in respuesta.ctidTraderAccount:
            print("--------------------------------")
            print("ACCOUNT ID:", cuenta.ctidTraderAccountId)
            print("TRADER LOGIN:", cuenta.traderLogin)
            print("ES LIVE:", cuenta.isLive)
            print("BROKER:", cuenta.brokerName)
            print("--------------------------------")

        print("================================")
        print("NO SE AUTENTICARA NINGUNA CUENTA")
        print("ESTA PRUEBA NO ABRE OPERACIONES")
        print("================================")

    else:
        print("CTRADER: OTRO MENSAJE RECIBIDO")


def iniciar_ctrader():
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
    print("================================")
    print("WEBHOOK RECIBIDO")
    print("Mensaje recibido:", request.get_data(as_text=True))
    print("================================")
    return "Webhook recibido correctamente"


print("INICIANDO HILO CTRADER")

threading.Thread(
    target=iniciar_ctrader,
    daemon=True
).start()
