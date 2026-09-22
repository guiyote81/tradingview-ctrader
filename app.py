```python
import os
import threading

from flask import Flask, request

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiMessages_pb2 import *

from twisted.internet import reactor


app = Flask(__name__)


# ============================================================
# CONFIGURACION
# ============================================================

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

# CUENTA DEMO
ACCOUNT_ID = 48481130


# ============================================================
# SIMBOLOS
# ============================================================

# NAS100
NAS100_SYMBOL_ID = 10014
NAS100_VOLUME = 10

# XAUUSD
XAUUSD_SYMBOL_ID = 41
XAUUSD_VOLUME = 100


# ============================================================
# ESTADO GLOBAL CTRADER
# ============================================================

ctrader_client = None

ctrader_conectado = False
aplicacion_autenticada = False
cuenta_autenticada = False

ctrader_iniciado = False


# ============================================================
# MOSTRAR ESTADO
# ============================================================

def mostrar_estado():

    print("================================")
    print("CTRADER: ESTADO ACTUAL")
    print("CLIENTE CREADO:", ctrader_client is not None)
    print("CONECTADO:", ctrader_conectado)
    print("APLICACION AUTENTICADA:", aplicacion_autenticada)
    print("CUENTA AUTENTICADA:", cuenta_autenticada)
    print("ACCOUNT ID:", ACCOUNT_ID)
    print("================================")


# ============================================================
# ERROR DE COMUNICACION
# ============================================================

def error_comunicacion(failure):

    print("================================")
    print("CTRADER: ERROR DE COMUNICACION")
    print(failure)
    print("================================")


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

    if volume == 10 or volume == 100:
        print("LOTES: 0.01")
    else:
        print("LOTES: VOLUMEN CONFIGURADO")

    print("LADO:", lado)
    print("CUENTA:", ACCOUNT_ID)
    print("================================")


    # --------------------------------------------------------
    # CLIENTE
    # --------------------------------------------------------

    if ctrader_client is None:

        print("CTRADER: ERROR - CLIENTE NO DISPONIBLE")

        mostrar_estado()

        return


    # --------------------------------------------------------
    # CUENTA
    # --------------------------------------------------------

    if not cuenta_autenticada:

        print("CTRADER: ERROR - CUENTA TODAVIA NO AUTENTICADA")

        mostrar_estado()

        return


    # --------------------------------------------------------
    # CREAR ORDEN
    # --------------------------------------------------------

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


    print("CTRADER: CLIENTE DISPONIBLE")
    print("CTRADER: CUENTA AUTENTICADA")
    print("CTRADER: ENVIANDO ORDEN")
    print("================================")


    try:

        deferred = ctrader_client.send(orden)

        deferred.addErrback(error_comunicacion)

        print("CTRADER: ORDEN ENVIADA AL SERVIDOR")

    except Exception as e:

        print("================================")
        print("CTRADER: EXCEPCION AL ENVIAR ORDEN")
        print("ERROR:", e)
        print("================================")


# ============================================================
# PROCESAR ALERTA TRADINGVIEW
# ============================================================

def procesar_alerta(mensaje):

    mensaje = mensaje.strip().upper()

    print("================================")
    print("CTRADER: PROCESANDO ALERTA")
    print("MENSAJE:", mensaje)
    print("================================")


    # ========================================================
    # NAS100
    # ========================================================

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


    # ========================================================
    # XAUUSD
    # ========================================================

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
# MENSAJES CTRADER
# ============================================================

def mensaje_recibido(client, message):

    global aplicacion_autenticada
    global cuenta_autenticada

    payload_type = message.payloadType

    print("================================")
    print("CTRADER: MENSAJE RECIBIDO")
    print("PAYLOAD TYPE:", payload_type)
    print("================================")


    # ========================================================
    # 2101 - APPLICATION AUTHENTICATED
    # ========================================================

    if payload_type == ProtoOAApplicationAuthRes().payloadType:

        aplicacion_autenticada = True

        print("================================")
        print("CTRADER: APLICACION AUTENTICADA")
        print("================================")


        if not ACCESS_TOKEN:

            print("CTRADER: ERROR - ACCESS TOKEN VACIO")

            return


        print("CTRADER: SOLICITANDO CUENTAS")


        cuenta_req = ProtoOAGetAccountListByAccessTokenReq()

        cuenta_req.accessToken = ACCESS_TOKEN


        try:

            deferred = client.send(cuenta_req)

            deferred.addErrback(error_comunicacion)

        except Exception as e:

            print("CTRADER: ERROR SOLICITANDO CUENTAS")
            print("ERROR:", e)

        return


    # ========================================================
    # ACCOUNT LIST
    # ========================================================

    if payload_type == ProtoOAGetAccountListByAccessTokenRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: RESPUESTA DE CUENTAS")
        print("================================")


        cuentas = respuesta.ctidTraderAccount

        print("CANTIDAD DE CUENTAS:", len(cuentas))


        cuenta_encontrada = False


        for cuenta in cuentas:

            account_id = int(
                cuenta.ctidTraderAccountId
            )

            print(
                "CUENTA ENCONTRADA:",
                account_id
            )


            if account_id == ACCOUNT_ID:

                cuenta_encontrada = True

                print("================================")
                print("CTRADER: CUENTA OBJETIVO ENCONTRADA")
                print("ACCOUNT ID:", ACCOUNT_ID)
                print("================================")


                cuenta_auth = ProtoOAAccountAuthReq()

                cuenta_auth.ctidTraderAccountId = ACCOUNT_ID
                cuenta_auth.accessToken = ACCESS_TOKEN


                print("CTRADER: AUTENTICANDO CUENTA")


                try:

                    deferred = client.send(cuenta_auth)

                    deferred.addErrback(error_comunicacion)

                except Exception as e:

                    print("CTRADER: ERROR AUTENTICANDO CUENTA")
                    print("ERROR:", e)

                break


        if not cuenta_encontrada:

            print("================================")
            print("CTRADER: ERROR")
            print("LA CUENTA OBJETIVO NO APARECE")
            print("ACCOUNT ID:", ACCOUNT_ID)
            print("================================")

        return


    # ========================================================
    # 2103 - ACCOUNT AUTHENTICATED
    # ========================================================

    if payload_type == ProtoOAAccountAuthRes().payloadType:

        respuesta = Protobuf.extract(message)

        cuenta_autenticada = True

        print("================================")
        print("CTRADER: CUENTA AUTENTICADA")
        print("ACCOUNT ID:",
              respuesta.ctidTraderAccountId)
        print("DEMO: SI")
        print("TRADING HABILITADO")
        print("================================")

        mostrar_estado()

        print("CTRADER: CLIENTE LISTO PARA OPERAR")

        print("================================")

        return


    # ========================================================
    # ERROR GENERAL
    # ========================================================

    if payload_type == ProtoOAErrorRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: ERROR GENERAL")
        print("ERROR CODE:", respuesta.errorCode)

        if respuesta.HasField("description"):

            print(
                "DESCRIPTION:",
                respuesta.description
            )

        print("================================")

        return


    # ========================================================
    # ERROR DE ORDEN
    # ========================================================

    if payload_type == ProtoOAOrderErrorEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: ERROR DE ORDEN")
        print("ERROR CODE:", respuesta.errorCode)

        if respuesta.HasField("description"):

            print(
                "DESCRIPTION:",
                respuesta.description
            )

        print("================================")

        return


    # ========================================================
    # EVENTO DE EJECUCION
    # ========================================================

    if payload_type == ProtoOAExecutionEvent().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: EVENTO DE EJECUCION")
        print("EXECUTION TYPE:",
              respuesta.executionType)


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


    # ========================================================
    # HEARTBEAT
    # ========================================================

    if payload_type == 51:

        print("CTRADER: HEARTBEAT OK")

        return


    print("CTRADER: MENSAJE NO PROCESADO")
    print("PAYLOAD TYPE:", payload_type)


# ============================================================
# CONECTADO
# ============================================================

def conectado_callback(client):

    global ctrader_conectado

    ctrader_conectado = True

    print("================================")
    print("CTRADER: CONECTADO")
    print("================================")


    print(
        "CTRADER: ENVIANDO AUTENTICACION DE APLICACION"
    )


    auth = ProtoOAApplicationAuthReq()

    auth.clientId = CLIENT_ID
    auth.clientSecret = CLIENT_SECRET


    try:

        deferred = client.send(auth)

        deferred.addErrback(error_comunicacion)

    except Exception as e:

        print("================================")
        print("CTRADER: ERROR EN AUTENTICACION")
        print("ERROR:", e)
        print("================================")


# ============================================================
# DESCONECTADO
# ============================================================

def desconectado_callback(client, reason):

    global ctrader_conectado
    global aplicacion_autenticada
    global cuenta_autenticada

    ctrader_conectado = False
    aplicacion_autenticada = False
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
    global ctrader_iniciado


    if ctrader_iniciado:

        print("CTRADER: YA ESTA INICIADO")

        return


    ctrader_iniciado = True


    print("================================")
    print("INICIANDO CTRADER")
    print("================================")


    # --------------------------------------------------------
    # VARIABLES
    # --------------------------------------------------------

    if not CLIENT_ID:

        print("CTRADER: FALTA CTRADER_CLIENT_ID")

    if not CLIENT_SECRET:

        print("CTRADER: FALTA CTRADER_CLIENT_SECRET")

    if not ACCESS_TOKEN:

        print("CTRADER: FALTA CTRADER_ACCESS_TOKEN")


    if not CLIENT_ID or not CLIENT_SECRET or not ACCESS_TOKEN:

        print("CTRADER: NO SE PUEDE INICIAR")

        return


    print("CTRADER: VARIABLES ENCONTRADAS")

    print(
        "CTRADER: CLIENT ID PRESENTE:",
        bool(CLIENT_ID)
    )

    print(
        "CTRADER: CLIENT SECRET PRESENTE:",
        bool(CLIENT_SECRET)
    )

    print(
        "CTRADER: ACCESS TOKEN PRESENTE:",
        bool(ACCESS_TOKEN)
    )


    # --------------------------------------------------------
    # CREAR CLIENTE DEMO
    # --------------------------------------------------------

    print("CTRADER: CREANDO CLIENTE DEMO")


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

    try:

        print("CTRADER: INICIANDO SERVICIO")

        ctrader_client.startService()

        print("CTRADER: SERVICIO INICIADO")

    except Exception as e:

        print("================================")
        print("CTRADER: ERROR STARTSERVICE")
        print("ERROR:", e)
        print("================================")

        return


    print("================================")
    print("CTRADER: EJECUTANDO REACTOR")
    print("================================")


    try:

        reactor.run(
            installSignalHandlers=False
        )

    except Exception as e:

        print("================================")
        print("CTRADER: ERROR REACTOR")
        print("ERROR:", e)
        print("================================")


# ============================================================
# FLASK
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return "Servidor TradingView cTrader funcionando"


# ============================================================
# STATUS
# ============================================================

@app.route("/status", methods=["GET"])
def status():

    return {
        "cliente_creado":
            ctrader_client is not None,

        "conectado":
            ctrader_conectado,

        "aplicacion_autenticada":
            aplicacion_autenticada,

        "cuenta_autenticada":
            cuenta_autenticada,

        "account_id":
            ACCOUNT_ID
    }


# ============================================================
# WEBHOOK
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    mensaje = request.get_data(
        as_text=True
    )


    print("================================")
    print("WEBHOOK RECIBIDO")
    print("Mensaje recibido:", mensaje)
    print("================================")


    procesar_alerta(mensaje)


    return "Webhook recibido correctamente"


# ============================================================
# INICIO CTRADER
# ============================================================

ctrader_thread = threading.Thread(
    target=iniciar_ctrader,
    daemon=True,
    name="CTRADER_THREAD"
)

ctrader_thread.start()


# ============================================================
# FLASK
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "10000")
        )
    )
```
