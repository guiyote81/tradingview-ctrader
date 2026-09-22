import os
import threading
import time

from flask import Flask, request, jsonify

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoHeartbeatEvent
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAAccountAuthReq,
    ProtoOAGetAccountListByAccessTokenReq,
    ProtoOANewOrderReq,
)
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATradeSide, ProtoOAOrderType
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoOAErrorRes
from twisted.internet import reactor


app = Flask(__name__)

# ============================================================
# VARIABLES CTRADER
# ============================================================

ctrader_client = None
ctrader_conectado = False
aplicacion_autenticada = False
cuenta_autenticada = False
ctrader_iniciado = False

ACCOUNT_ID = 48481130

# ============================================================
# FUNCION PARA ABRIR OPERACION
# ============================================================

def abrir_operacion(symbol_id, volume, side, nombre_simbolo):
    global ctrader_client, cuenta_autenticada

    print("=================================")
    print("CTRADER: INTENTANDO ABRIR OPERACION")
    print("SIMBOLO:", nombre_simbolo)
    print("SYMBOL ID:", symbol_id)
    print("VOLUMEN:", volume)
    print("LADO:", side)
    print("CUENTA:", ACCOUNT_ID)
    print("=================================")

    if ctrader_client is None:
        print("CTRADER: ERROR - CLIENTE NO DISPONIBLE")
        return

    if not cuenta_autenticada:
        print("CTRADER: ERROR - CUENTA NO AUTENTICADA")
        return

    try:
        request_order = ProtoOANewOrderReq()

        request_order.ctidTraderAccountId = ACCOUNT_ID
        request_order.symbolId = symbol_id
        request_order.orderType = ProtoOAOrderType.MARKET
        request_order.tradeSide = side
        request_order.volume = volume
        request_order.label = "SR_M30_RETEST"

        print("CTRADER: ENVIANDO ORDEN")

        reactor.callFromThread(
            ctrader_client.send,
            request_order
        )

        print("CTRADER: ORDEN ENVIADA")

    except Exception as e:
        print("CTRADER: ERROR AL ENVIAR ORDEN:", str(e))


# ============================================================
# PROCESAR ALERTA DE TRADINGVIEW
# ============================================================

def procesar_alerta(mensaje):
    mensaje = mensaje.upper()

    print("=================================")
    print("CTRADER: PROCESANDO ALERTA")
    print("MENSAJE:", mensaje)
    print("=================================")

    # --------------------------------------------------------
    # DETERMINAR SIMBOLO
    # --------------------------------------------------------

    if "XAUUSD" in mensaje or "ORO" in mensaje:
        symbol_id = 41
        nombre_simbolo = "XAUUSD"
        volume = 100

    elif "NAS100" in mensaje or "NASDAQ" in mensaje:
        symbol_id = 10014
        nombre_simbolo = "NAS100"
        volume = 10

    else:
        print("CTRADER: SIMBOLO NO RECONOCIDO")
        return

    # --------------------------------------------------------
    # DETERMINAR OPERACION
    # --------------------------------------------------------

    if "VENTA" in mensaje or "SELL" in mensaje:
        side = ProtoOATradeSide.SELL
        print("CTRADER: ALERTA", nombre_simbolo, "VENTA")

    elif "COMPRA" in mensaje or "BUY" in mensaje:
        side = ProtoOATradeSide.BUY
        print("CTRADER: ALERTA", nombre_simbolo, "COMPRA")

    else:
        print("CTRADER: TIPO DE OPERACION NO RECONOCIDO")
        return

    abrir_operacion(
        symbol_id,
        volume,
        side,
        nombre_simbolo
    )


# ============================================================
# CALLBACK CTRADER
# ============================================================

def mensaje_recibido(client, message):
    global ctrader_conectado
    global aplicacion_autenticada
    global cuenta_autenticada

    try:

        payload_type = message.payloadType

        # ----------------------------------------------------
        # HEARTBEAT
        # ----------------------------------------------------

        if payload_type == 51:
            print("CTRADER: HEARTBEAT")
            return

        # ----------------------------------------------------
        # AUTENTICACION DE APLICACION
        # ----------------------------------------------------

        if payload_type == ProtoOAApplicationAuthReq().payloadType:
            print("CTRADER: MENSAJE DE AUTENTICACION RECIBIDO")

        # ----------------------------------------------------
        # RESPUESTA AUTENTICACION APP
        # ----------------------------------------------------

        if payload_type == 2100:

            print("=================================")
            print("CTRADER: APLICACION AUTENTICADA")
            print("=================================")

            aplicacion_autenticada = True

            request_accounts = ProtoOAGetAccountListByAccessTokenReq()

            request_accounts.accessToken = os.getenv(
                "CTRADER_ACCESS_TOKEN"
            )

            print("CTRADER: SOLICITANDO CUENTAS")

            client.send(request_accounts)

            return

        # ----------------------------------------------------
        # LISTA DE CUENTAS
        # ----------------------------------------------------

        if payload_type == 2115:

            print("CTRADER: RESPUESTA LISTA DE CUENTAS")

            response = Protobuf.extract(message)

            print("CTRADER: CUENTAS ENCONTRADAS")

            cuentas = getattr(response, "ctidTraderAccount", [])

            cuenta_encontrada = False

            for cuenta in cuentas:

                print(
                    "CTRADER: CUENTA:",
                    cuenta.ctidTraderAccountId
                )

                if cuenta.ctidTraderAccountId == ACCOUNT_ID:

                    cuenta_encontrada = True

                    print(
                        "CTRADER: CUENTA OBJETIVO ENCONTRADA"
                    )

                    auth_account = ProtoOAAccountAuthReq()

                    auth_account.ctidTraderAccountId = ACCOUNT_ID

                    auth_account.accessToken = os.getenv(
                        "CTRADER_ACCESS_TOKEN"
                    )

                    print(
                        "CTRADER: AUTENTICANDO CUENTA"
                    )

                    client.send(auth_account)

                    break

            if not cuenta_encontrada:
                print(
                    "CTRADER: ERROR - CUENTA",
                    ACCOUNT_ID,
                    "NO ENCONTRADA"
                )

            return

        # ----------------------------------------------------
        # CUENTA AUTENTICADA
        # ----------------------------------------------------

        if payload_type == 2101:

            print("=================================")
            print("CTRADER: CUENTA AUTENTICADA")
            print("=================================")

            cuenta_autenticada = True

            print(
                "CTRADER: CLIENTE LISTO PARA OPERAR"
            )

            return

        # ----------------------------------------------------
        # ERROR CTRADER
        # ----------------------------------------------------

        if payload_type == 2142:

            response = Protobuf.extract(message)

            print("=================================")
            print("CTRADER: ERROR")
            print(response)
            print("=================================")

            return

        # ----------------------------------------------------
        # ERROR DE ORDEN
        # ----------------------------------------------------

        if payload_type == 2122:

            response = Protobuf.extract(message)

            print("=================================")
            print("CTRADER: ERROR DE ORDEN")
            print(response)
            print("=================================")

            return

        # ----------------------------------------------------
        # EJECUCION
        # ----------------------------------------------------

        if payload_type == 2126:

            response = Protobuf.extract(message)

            print("=================================")
            print("CTRADER: EJECUCION RECIBIDA")
            print(response)
            print("=================================")

            return

    except Exception as e:

        print(
            "CTRADER: ERROR EN CALLBACK:",
            str(e)
        )


# ============================================================
# CALLBACK CONEXION
# ============================================================

def conectado_callback(client):
    global ctrader_conectado

    print("=================================")
    print("CTRADER: CONECTADO")
    print("=================================")

    ctrader_conectado = True

    client_id = os.getenv(
        "CTRADER_CLIENT_ID"
    )

    client_secret = os.getenv(
        "CTRADER_CLIENT_SECRET"
    )

    print(
        "CTRADER: ENVIANDO AUTENTICACION DE APLICACION"
    )

    auth_request = ProtoOAApplicationAuthReq()

    auth_request.clientId = client_id
    auth_request.clientSecret = client_secret

    client.send(auth_request)


# ============================================================
# INICIAR CTRADER
# ============================================================

def iniciar_ctrader():

    global ctrader_client
    global ctrader_iniciado

    print("=================================")
    print("INICIANDO CTRADER")
    print("=================================")

    client_id = os.getenv(
        "CTRADER_CLIENT_ID"
    )

    client_secret = os.getenv(
        "CTRADER_CLIENT_SECRET"
    )

    access_token = os.getenv(
        "CTRADER_ACCESS_TOKEN"
    )

    print(
        "CTRADER: VARIABLES ENCONTRADAS"
    )

    print(
        "CTRADER: CLIENT ID PRESENTE:",
        bool(client_id)
    )

    print(
        "CTRADER: CLIENT SECRET PRESENTE:",
        bool(client_secret)
    )

    print(
        "CTRADER: ACCESS TOKEN PRESENTE:",
        bool(access_token)
    )

    if not client_id or not client_secret or not access_token:

        print(
            "CTRADER: ERROR - FALTAN VARIABLES"
        )

        return

    try:

        print(
            "CTRADER: CREANDO CLIENTE DEMO"
        )

        ctrader_client = Client(
            EndPoints.PROTOBUF_DEMO_HOST,
            EndPoints.PROTOBUF_PORT,
            TcpProtocol
        )

        print(
            "CTRADER: CLIENTE CREADO"
        )

        ctrader_client.setConnectedCallback(
            conectado_callback
        )

        ctrader_client.setMessageReceivedCallback(
            mensaje_recibido
        )

        print(
            "CTRADER: CALLBACKS CONFIGURADOS"
        )

        print(
            "CTRADER: INICIANDO SERVICIO"
        )

        ctrader_client.startService()

        ctrader_iniciado = True

        print(
            "CTRADER: SERVICIO INICIADO"
        )

        print("=================================")
        print("CTRADER: INICIANDO REACTOR")
        print("=================================")

        reactor.run(
            installSignalHandlers=False
        )

    except Exception as e:

        print(
            "CTRADER: ERROR AL INICIAR:",
            str(e)
        )


# ============================================================
# WEBHOOK TRADINGVIEW
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:

        data = request.get_json(
            silent=True
        )

        if data is None:

            mensaje = request.data.decode(
                "utf-8",
                errors="ignore"
            )

        elif isinstance(data, dict):

            mensaje = (
                data.get("message")
                or data.get("alert")
                or str(data)
            )

        else:

            mensaje = str(data)

        print("=================================")
        print("WEBHOOK RECIBIDO")
        print("MENSAJE RECIBIDO:", mensaje)
        print("=================================")

        procesar_alerta(
            mensaje
        )

        return jsonify(
            {
                "status": "ok",
                "message": "Alerta recibida"
            }
        ), 200

    except Exception as e:

        print(
            "WEBHOOK ERROR:",
            str(e)
        )

        return jsonify(
            {
                "status": "error",
                "error": str(e)
            }
        ), 500


# ============================================================
# ESTADO
# ============================================================

@app.route("/status", methods=["GET"])
def status():

    return jsonify(
        {
            "ctrader_iniciado": ctrader_iniciado,
            "ctrader_conectado": ctrader_conectado,
            "aplicacion_autenticada": aplicacion_autenticada,
            "cuenta_autenticada": cuenta_autenticada,
            "account_id": ACCOUNT_ID
        }
    )


# ============================================================
# PAGINA PRINCIPAL
# ============================================================

@app.route("/", methods=["GET"])
def inicio():

    return (
        "Servidor TradingView cTrader funcionando"
    )


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

    app.run(...)
                10000
            )
        )
    )
