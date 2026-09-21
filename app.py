```python
import os
import threading
import time

from flask import Flask, request

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiMessages_pb2 import *


app = Flask(__name__)


# ============================================================
# VARIABLES
# ============================================================

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

ACCOUNT_ID = 48481130

NAS100_SYMBOL_ID = 10014
NAS100_VOLUME = 10

XAUUSD_SYMBOL_ID = 41
XAUUSD_VOLUME = 100


ctrader_client = None
cuenta_autenticada = False


# ============================================================
# INICIO
# ============================================================

print("================================")
print("INICIANDO CTRADER")
print("================================")

if CLIENT_ID:
    print("CTRADER: VARIABLE CLIENT ID ENCONTRADA")
else:
    print("CTRADER: FALTA CLIENT ID")

if CLIENT_SECRET:
    print("CTRADER: VARIABLE CLIENT SECRET ENCONTRADA")
else:
    print("CTRADER: FALTA CLIENT SECRET")

if ACCESS_TOKEN:
    print("CTRADER: VARIABLE ACCESS TOKEN ENCONTRADA")
else:
    print("CTRADER: FALTA ACCESS TOKEN")


# ============================================================
# ABRIR OPERACION
# ============================================================

def abrir_operacion(simbolo, direccion):

    global ctrader_client
    global cuenta_autenticada

    print("================================")
    print("CTRADER: INTENTANDO ABRIR OPERACION")
    print("SIMBOLO:", simbolo)
    print("DIRECCION:", direccion)
    print("================================")

    if ctrader_client is None:
        print("CTRADER: CLIENTE NO DISPONIBLE")
        return

    if not cuenta_autenticada:
        print("CTRADER: CUENTA TODAVIA NO AUTENTICADA")
        return

    if simbolo == "NAS100":
        symbol_id = NAS100_SYMBOL_ID
        volume = NAS100_VOLUME

    elif simbolo == "XAUUSD":
        symbol_id = XAUUSD_SYMBOL_ID
        volume = XAUUSD_VOLUME

    else:
        print("CTRADER: SIMBOLO NO RECONOCIDO")
        return

    orden = ProtoOANewOrderReq()

    orden.ctidTraderAccountId = ACCOUNT_ID
    orden.symbolId = symbol_id
    orden.orderType = ProtoOAOrderType.MARKET

    if direccion == "BUY":
        orden.tradeSide = ProtoOATradeSide.BUY

    elif direccion == "SELL":
        orden.tradeSide = ProtoOATradeSide.SELL

    else:
        print("CTRADER: DIRECCION NO RECONOCIDA")
        return

    orden.volume = volume
    orden.label = "TV_" + simbolo

    print("================================")
    print("CTRADER: ENVIANDO ORDEN")
    print("SYMBOL ID:", symbol_id)
    print("VOLUMEN:", volume)
    print("DIRECCION:", direccion)
    print("================================")

    try:
        ctrader_client.send(orden)

    except Exception as e:
        print("CTRADER: ERROR ENVIANDO ORDEN")
        print("ERROR:", e)


# ============================================================
# PROCESAR ALERTA
# ============================================================

def procesar_alerta(mensaje):

    mensaje = mensaje.strip().upper()

    print("================================")
    print("CTRADER: PROCESANDO ALERTA")
    print("MENSAJE:", mensaje)
    print("================================")

    if "NAS100" in mensaje or "NASDAQ" in mensaje:

        if "COMPRA" in mensaje or "BUY" in mensaje:
            abrir_operacion("NAS100", "BUY")

        elif "VENTA" in mensaje or "SELL" in mensaje:
            abrir_operacion("NAS100", "SELL")

        else:
            print("CTRADER: NO SE ENCONTRO COMPRA O VENTA")

    elif "XAUUSD" in mensaje or "ORO" in mensaje:

        if "COMPRA" in mensaje or "BUY" in mensaje:
            abrir_operacion("XAUUSD", "BUY")

        elif "VENTA" in mensaje or "SELL" in mensaje:
            abrir_operacion("XAUUSD", "SELL")

        else:
            print("CTRADER: NO SE ENCONTRO COMPRA O VENTA")

    else:
        print("CTRADER: SIMBOLO NO RECONOCIDO")


# ============================================================
# MENSAJES CTRADER
# ============================================================

def mensaje_recibido(client, message):

    global cuenta_autenticada

    print("================================")
    print("CTRADER: MENSAJE RECIBIDO")

    try:
        print("PAYLOAD TYPE:", message.payloadType)
    except Exception:
        pass

    print("================================")


    # --------------------------------------------------------
    # APLICACION AUTENTICADA
    # --------------------------------------------------------

    if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

        print("CTRADER: APLICACION AUTENTICADA")
        print("CTRADER: SOLICITANDO CUENTAS")

        solicitud = ProtoOAGetAccountListByAccessTokenReq()
        solicitud.accessToken = ACCESS_TOKEN

        try:
            client.send(solicitud)
            print("CTRADER: SOLICITUD DE CUENTAS ENVIADA")

        except Exception as e:
            print("CTRADER: ERROR SOLICITANDO CUENTAS")
            print("ERROR:", e)

        return


    # --------------------------------------------------------
    # LISTA DE CUENTAS
    # --------------------------------------------------------

    if message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:

        print("CTRADER: LISTA DE CUENTAS RECIBIDA")

        respuesta = Protobuf.extract(message)

        try:

            cantidad = len(respuesta.ctidTraderAccount)

            print("CTRADER: CANTIDAD DE CUENTAS:", cantidad)

            cuenta_encontrada = False

            for cuenta in respuesta.ctidTraderAccount:

                print("--------------------------------")
                print("ACCOUNT ID:", cuenta.ctidTraderAccountId)
                print("TRADER LOGIN:", cuenta.traderLogin)
                print("ES LIVE:", cuenta.isLive)
                print("--------------------------------")

                if int(cuenta.ctidTraderAccountId) == ACCOUNT_ID:

                    cuenta_encontrada = True

                    print("CTRADER: CUENTA OBJETIVO ENCONTRADA")

            if not cuenta_encontrada:

                print("CTRADER: NO SE ENCONTRO LA CUENTA")
                print("ACCOUNT ID BUSCADO:", ACCOUNT_ID)

                return

            solicitud_auth = ProtoOAAccountAuthReq()

            solicitud_auth.ctidTraderAccountId = ACCOUNT_ID
            solicitud_auth.accessToken = ACCESS_TOKEN

            print("CTRADER: AUTENTICANDO CUENTA")

            client.send(solicitud_auth)

        except Exception as e:

            print("CTRADER: ERROR PROCESANDO CUENTAS")
            print("ERROR:", e)

        return


    # --------------------------------------------------------
    # CUENTA AUTENTICADA
    # --------------------------------------------------------

    if message.payloadType == ProtoOAAccountAuthRes().payloadType:

        respuesta = Protobuf.extract(message)

        cuenta_autenticada = True

        print("================================")
        print("CTRADER: CUENTA CTRADER AUTENTICADA")
        print("ACCOUNT ID:", ACCOUNT_ID)
        print("================================")

        return


    # --------------------------------------------------------
    # ERROR GENERAL
    # --------------------------------------------------------

    if message.payloadType == ProtoOAErrorRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: ERROR GENERAL")
        print("================================")

        try:
            print("ERROR CODE:", respuesta.errorCode)
        except Exception:
            print("ERROR CODE: NO DISPONIBLE")

        try:
            print("DESCRIPTION:", respuesta.description)
        except Exception:
            print("DESCRIPTION: NO DISPONIBLE")

        print("================================")

        return


    # --------------------------------------------------------
    # ERROR DE ORDEN
    # --------------------------------------------------------

    if message.payloadType == ProtoOAOrderErrorEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: ERROR DE ORDEN")
        print("================================")

        try:
            print("ERROR CODE:", respuesta.errorCode)
        except Exception:
            pass

        try:
            print("DESCRIPTION:", respuesta.description)
        except Exception:
            pass

        return


    # --------------------------------------------------------
    # EJECUCION
    # --------------------------------------------------------

    if message.payloadType == ProtoOAExecutionEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: EVENTO DE EJECUCION")
        print("================================")

        try:
            print("EXECUTION TYPE:", respuesta.executionType)
        except Exception:
            pass

        if respuesta.HasField("order"):

            print("ORDER ID:", respuesta.order.orderId)
            print("ORDER STATUS:", respuesta.order.orderStatus)

        if respuesta.HasField("position"):

            print("POSITION ID:", respuesta.position.positionId)

        if respuesta.HasField("deal"):

            print("DEAL ID:", respuesta.deal.dealId)

        return


    # --------------------------------------------------------
    # HEARTBEAT
    # --------------------------------------------------------

    if message.payloadType == ProtoHeartbeatEvent().payloadType:

        print("CTRADER: HEARTBEAT RECIBIDO")

        return


    # --------------------------------------------------------
    # OTROS MENSAJES
    # --------------------------------------------------------

    print("CTRADER: TIPO DE MENSAJE NO IDENTIFICADO")
    print("PAYLOAD TYPE:", message.payloadType)


# ============================================================
# CONECTADO
# ============================================================

def conectado_callback(client):

    global ctrader_client

    ctrader_client = client

    print("================================")
    print("CTRADER: CONECTADO")
    print("================================")

    solicitud = ProtoOAApplicationAuthReq()

    solicitud.clientId = CLIENT_ID
    solicitud.clientSecret = CLIENT_SECRET

    print("CTRADER: ENVIANDO AUTENTICACION")

    try:
        client.send(solicitud)

    except Exception as e:

        print("CTRADER: ERROR ENVIANDO AUTENTICACION")
        print("ERROR:", e)


# ============================================================
# DESCONECTADO
# ============================================================

def desconectado_callback(client, reason):

    global ctrader_client
    global cuenta_autenticada

    print("================================")
    print("CTRADER: DESCONECTADO")
    print("MOTIVO:", reason)
    print("================================")

    ctrader_client = None
    cuenta_autenticada = False


# ============================================================
# INICIAR CTRADER
# ============================================================

def iniciar_ctrader():

    while True:

        try:

            print("================================")
            print("CTRADER: CREANDO CLIENTE DEMO")
            print("================================")

            client = Client(
                EndPoints.PROTOBUF_DEMO_HOST,
                EndPoints.PROTOBUF_PORT,
                TcpProtocol
            )

            print("CTRADER: CLIENTE CREADO")

            client.setConnectedCallback(conectado_callback)
            client.setDisconnectedCallback(desconectado_callback)
            client.setMessageReceivedCallback(mensaje_recibido)

            print("CTRADER: CALLBACKS CONFIGURADOS")
            print("CTRADER: INICIANDO SERVICIO")

            client.startService()

            print("CTRADER: SERVICIO INICIADO")

            from twisted.internet import reactor

            if not reactor.running:
                reactor.run()

        except Exception as e:

            print("================================")
            print("CTRADER: ERROR EN SERVICIO")
            print("ERROR:", e)
            print("================================")

            time.sleep(10)


# ============================================================
# WEBHOOK
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return "Servidor TradingView cTrader funcionando"


@app.route("/status", methods=["GET"])
def status():

    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():

    print("================================")
    print("WEBHOOK RECIBIDO")
    print("================================")

    mensaje = request.get_data(as_text=True)

    print("Mensaje recibido:", mensaje)

    procesar_alerta(mensaje)

    print("================================")

    return "Webhook recibido correctamente"


# ============================================================
# HILO CTRADER
# ============================================================

threading.Thread(
    target=iniciar_ctrader,
    daemon=True
).start()


# ============================================================
# FLASK
# ============================================================

if __name__ == "__main__":

    puerto = int(os.environ.get("PORT", 10000))

    print("================================")
    print("FLASK INICIADO")
    print("PUERTO:", puerto)
    print("================================")

    app.run(
        host="0.0.0.0",
        port=puerto
    )
```
