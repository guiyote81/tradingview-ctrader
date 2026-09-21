import os
import threading
import time

from flask import Flask, request

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiMessages_pb2 import *

app = Flask(__name__)

# ============================================================
# CONFIGURACION
# ============================================================

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

# Cuenta DEMO confirmada
ACCOUNT_ID = 48481130

# NAS100 confirmado
NAS100_SYMBOL_ID = 10014
NAS100_VOLUME = 10

# XAUUSD confirmado
XAUUSD_SYMBOL_ID = 41
XAUUSD_VOLUME = 100

# Estado
ctrader_client = None
cuenta_autenticada = False


# ============================================================
# ABRIR OPERACION
# ============================================================

def abrir_operacion(nombre, symbol_id, volume, lado):
    global ctrader_client
    global cuenta_autenticada

    print("================================")
    print("CTRADER: INTENTANDO ABRIR OPERACION")
    print("SIMBOLO:", nombre)
    print("SYMBOL ID:", symbol_id)
    print("VOLUMEN:", volume)
    print("LOTES:", "0.01")
    print("LADO:", lado)
    print("CUENTA:", ACCOUNT_ID)
    print("================================")

    if ctrader_client is None:
        print("CTRADER: ERROR - CLIENTE NO DISPONIBLE")
        return

    if not cuenta_autenticada:
        print("CTRADER: ERROR - CUENTA TODAVIA NO AUTENTICADA")
        return

    orden = ProtoOANewOrderReq()

    orden.ctidTraderAccountId = ACCOUNT_ID
    orden.symbolId = symbol_id
    orden.orderType = ProtoOAOrderType.MARKET

    if lado == "BUY":
        orden.tradeSide = ProtoOATradeSide.BUY
    else:
        orden.tradeSide = ProtoOATradeSide.SELL

    orden.volume = volume
    orden.label = "TV_" + nombre

    print("CTRADER: ENVIANDO ORDEN")
    print("================================")

    deferred = ctrader_client.send(orden)

    def error_orden(failure):
        print("================================")
        print("CTRADER: ERROR AL ENVIAR ORDEN")
        print(failure)
        print("================================")

    deferred.addErrback(error_orden)


# ============================================================
# PROCESAR ALERTA DE TRADINGVIEW
# ============================================================

def procesar_alerta(mensaje):
    mensaje = mensaje.strip().upper()

    print("================================")
    print("CTRADER: PROCESANDO ALERTA")
    print("MENSAJE:", mensaje)
    print("================================")

    # --------------------------------------------------------
    # NAS100 / NASDAQ
    # --------------------------------------------------------

    if "NAS100" in mensaje or "NASDAQ" in mensaje:

        if "COMPRA" in mensaje or "BUY" in mensaje:

            print("CTRADER: ALERTA NAS100 COMPRA")

            abrir_operacion(
                "NAS100",
                NAS100_SYMBOL_ID,
                NAS100_VOLUME,
                "BUY"
            )

            return

        if "VENTA" in mensaje or "SELL" in mensaje:

            print("CTRADER: ALERTA NAS100 VENTA")

            abrir_operacion(
                "NAS100",
                NAS100_SYMBOL_ID,
                NAS100_VOLUME,
                "SELL"
            )

            return

    # --------------------------------------------------------
    # XAUUSD / ORO
    # --------------------------------------------------------

    if "XAUUSD" in mensaje or "ORO" in mensaje:

        if "COMPRA" in mensaje or "BUY" in mensaje:

            print("CTRADER: ALERTA XAUUSD COMPRA")

            abrir_operacion(
                "XAUUSD",
                XAUUSD_SYMBOL_ID,
                XAUUSD_VOLUME,
                "BUY"
            )

            return

        if "VENTA" in mensaje or "SELL" in mensaje:

            print("CTRADER: ALERTA XAUUSD VENTA")

            abrir_operacion(
                "XAUUSD",
                XAUUSD_SYMBOL_ID,
                XAUUSD_VOLUME,
                "SELL"
            )

            return

    print("CTRADER: ALERTA NO RECONOCIDA")


# ============================================================
# MENSAJES RECIBIDOS DESDE CTRADER
# ============================================================

def mensaje_recibido(client, message):
    global cuenta_autenticada

    print("================================")
    print("CTRADER: MENSAJE RECIBIDO")
    print("PAYLOAD TYPE:", message.payloadType)
    print("================================")

    # --------------------------------------------------------
    # 2101 - APLICACION AUTENTICADA
    # --------------------------------------------------------

    if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

        print("CTRADER: APLICACION AUTENTICADA")
        print("CTRADER: SOLICITANDO CUENTAS")

        cuenta_req = ProtoOAGetAccountListByAccessTokenReq()
        cuenta_req.accessToken = ACCESS_TOKEN

        deferred = client.send(cuenta_req)

        def error_cuentas(failure):
            print("================================")
            print("CTRADER: ERROR AL SOLICITAR CUENTAS")
            print(failure)
            print("================================")

        deferred.addErrback(error_cuentas)

        return

    # --------------------------------------------------------
    # 2150 - LISTA DE CUENTAS
    # --------------------------------------------------------

    if message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: LISTA DE CUENTAS RECIBIDA")
        print("================================")

        cuentas = respuesta.ctidTraderAccount

        print("CANTIDAD DE CUENTAS:", len(cuentas))

        cuenta_encontrada = False

        for cuenta in cuentas:

            print("CUENTA ENCONTRADA:", cuenta.ctidTraderAccountId)

            if int(cuenta.ctidTraderAccountId) == ACCOUNT_ID:

                cuenta_encontrada = True

                print("CTRADER: CUENTA OBJETIVO ENCONTRADA")
                print("ACCOUNT ID:", ACCOUNT_ID)

                cuenta_auth = ProtoOAAccountAuthReq()

                cuenta_auth.ctidTraderAccountId = ACCOUNT_ID
                cuenta_auth.accessToken = ACCESS_TOKEN

                print("CTRADER: AUTENTICANDO CUENTA")

                deferred = client.send(cuenta_auth)

                def error_auth(failure):
                    print("================================")
                    print("CTRADER: ERROR AL AUTENTICAR CUENTA")
                    print(failure)
                    print("================================")

                deferred.addErrback(error_auth)

                break

        if not cuenta_encontrada:

            print("================================")
            print("CTRADER: ERROR")
            print("LA CUENTA OBJETIVO NO APARECE EN LA LISTA")
            print("ACCOUNT ID BUSCADO:", ACCOUNT_ID)
            print("================================")

        return

    # --------------------------------------------------------
    # 2103 - CUENTA AUTENTICADA
    # --------------------------------------------------------

    if message.payloadType == ProtoOAAccountAuthRes().payloadType:

        respuesta = Protobuf.extract(message)

        cuenta_autenticada = True

        print("================================")
        print("CTRADER: CUENTA CTRADER AUTENTICADA")
        print("ACCOUNT ID:", respuesta.ctidTraderAccountId)
        print("DEMO: SI")
        print("TRADING HABILITADO")
        print("================================")

        return

    # --------------------------------------------------------
    # 2142 - ERROR GENERAL DE CTRADER
    # --------------------------------------------------------

    if message.payloadType == ProtoOAErrorRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: ERROR 2142")
        print("ERROR CODE:", respuesta.errorCode)

        if respuesta.HasField("description"):
            print("DESCRIPTION:", respuesta.description)

        print("================================")

        return

    # --------------------------------------------------------
    # 2132 - ERROR DE ORDEN
    # --------------------------------------------------------

    if message.payloadType == ProtoOAOrderErrorEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: ERROR DE ORDEN")
        print("ERROR CODE:", respuesta.errorCode)

        if respuesta.HasField("description"):
            print("DESCRIPTION:", respuesta.description)

        print("================================")

        return

    # --------------------------------------------------------
    # 2126 - EVENTO DE EJECUCION
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
    # 51 - HEARTBEAT
    # --------------------------------------------------------

    if message.payloadType == 51:

        print("CTRADER: HEARTBEAT OK")

        return

    # --------------------------------------------------------
    # OTROS MENSAJES
    # --------------------------------------------------------

    print("CTRADER: MENSAJE NO PROCESADO")
    print("PAYLOAD TYPE:", message.payloadType)


# ============================================================
# CONEXION
# ============================================================

def conectado_callback(client):
    print("================================")
    print("CTRADER: CONECTADO")
    print("================================")

    auth = ProtoOAApplicationAuthReq()

    auth.clientId = CLIENT_ID
    auth.clientSecret = CLIENT_SECRET

    print("CTRADER: ENVIANDO AUTENTICACION")
    print("================================")

    deferred = client.send(auth)

    def error_auth(failure):
        print("================================")
        print("CTRADER: ERROR EN AUTENTICACION")
        print(failure)
        print("================================")

    deferred.addErrback(error_auth)


# ============================================================
# DESCONEXION
# ============================================================

def desconectado_callback(client, reason):
    global cuenta_autenticada

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

    if not CLIENT_ID or not CLIENT_SECRET or not ACCESS_TOKEN:

        print("CTRADER: FALTAN VARIABLES DE ENTORNO")

        if not CLIENT_ID:
            print("FALTA CTRADER_CLIENT_ID")

        if not CLIENT_SECRET:
            print("FALTA CTRADER_CLIENT_SECRET")

        if not ACCESS_TOKEN:
            print("FALTA CTRADER_ACCESS_TOKEN")

        return

    print("CTRADER: VARIABLES ENCONTRADAS")
    print("CTRADER: CREANDO CLIENTE DEMO")

    ctrader_client = Client(
        EndPoints.PROTOBUF_DEMO_HOST,
        EndPoints.PROTOBUF_PORT,
        TcpProtocol
    )

    print("CTRADER: CLIENTE CREADO")

    ctrader_client.setConnectedCallback(conectado_callback)
    ctrader_client.setDisconnectedCallback(desconectado_callback)
    ctrader_client.setMessageReceivedCallback(mensaje_recibido)

    print("CTRADER: CALLBACKS CONFIGURADOS")
    print("CTRADER: INICIANDO SERVICIO")

    ctrader_client.startService()

    print("CTRADER: SERVICIO INICIADO")
    print("================================")

    while True:
        time.sleep(60)


# ============================================================
# FLASK
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return "Servidor TradingView cTrader funcionando"


@app.route("/status", methods=["GET"])
def status():
    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():

    mensaje = request.get_data(as_text=True)

    print("================================")
    print("WEBHOOK RECIBIDO")
    print("Mensaje recibido:", mensaje)
    print("================================")

    procesar_alerta(mensaje)

    return "Webhook recibido correctamente"


# ============================================================
# INICIAR CTRADER EN SEGUNDO PLANO
# ============================================================

threading.Thread(
    target=iniciar_ctrader,
    daemon=True
).start()


# ============================================================
# INICIAR FLASK
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
