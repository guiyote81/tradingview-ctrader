```python
import os
import threading
import time

from flask import Flask, request

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiMessages_pb2 import *


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# VARIABLES
# ============================================================

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

ACCOUNT_ID = 48481130

# Símbolos confirmados
NAS100_SYMBOL_ID = 10014
NAS100_VOLUME = 10       # 0.01 lote

XAUUSD_SYMBOL_ID = 41
XAUUSD_VOLUME = 100      # 0.01 lote


# ============================================================
# ESTADO
# ============================================================

ctrader_client = None
cuenta_autenticada = False


# ============================================================
# INFORMACION INICIAL
# ============================================================

print("================================")
print("INICIANDO CTRADER")
print("================================")

if CLIENT_ID:
    print("CTRADER: VARIABLE CLIENT ID ENCONTRADA")
else:
    print("CTRADER: FALTA CTRADER_CLIENT_ID")

if CLIENT_SECRET:
    print("CTRADER: VARIABLE CLIENT SECRET ENCONTRADA")
else:
    print("CTRADER: FALTA CTRADER_CLIENT_SECRET")

if ACCESS_TOKEN:
    print("CTRADER: VARIABLE ACCESS TOKEN ENCONTRADA")
else:
    print("CTRADER: FALTA CTRADER_ACCESS_TOKEN")


# ============================================================
# FUNCION PARA ABRIR OPERACION
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
        print("CTRADER: SIMBOLO NO RECONOCIDO:", simbolo)
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

    # Por ahora NO colocamos SL/TP.
    # Primero comprobamos que la autenticacion y la orden
    # basica funcionen correctamente.

    orden.label = "TV_" + simbolo

    print("================================")
    print("CTRADER: ENVIANDO ORDEN")
    print("SIMBOLO ID:", symbol_id)
    print("VOLUMEN:", volume)
    print("DIRECCION:", direccion)
    print("================================")

    try:
        ctrader_client.send(orden)

    except Exception as e:
        print("CTRADER: ERROR ENVIANDO ORDEN")
        print("ERROR:", e)


# ============================================================
# PROCESAR WEBHOOK
# ============================================================

def procesar_alerta(mensaje):

    mensaje = mensaje.strip().upper()

    print("================================")
    print("CTRADER: PROCESANDO ALERTA")
    print("MENSAJE:", mensaje)
    print("================================")

    # NAS100
    if "NAS100" in mensaje or "NASDAQ" in mensaje:

        if "COMPRA" in mensaje or "BUY" in mensaje:
            abrir_operacion("NAS100", "BUY")

        elif "VENTA" in mensaje or "SELL" in mensaje:
            abrir_operacion("NAS100", "SELL")

        else:
            print("CTRADER: NO SE ENCONTRO COMPRA O VENTA")

    # XAUUSD
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
# MENSAJES RECIBIDOS DE CTRADER
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
    # 2101 - APLICACION AUTENTICADA
    # --------------------------------------------------------

    if message.payloadType == ProtoOAApplicationAuthRes().payloadType:

        print("CTRADER: APLICACION AUTENTICADA")
        print("CTRADER: SOLICITANDO CUENTAS CON ACCESS TOKEN")

        solicitud_cuentas = ProtoOAGetAccountListByAccessTokenReq()
        solicitud_cuentas.accessToken = ACCESS_TOKEN

        try:
            client.send(solicitud_cuentas)
            print("CTRADER: SOLICITUD DE CUENTAS ENVIADA")

        except Exception as e:
            print("CTRADER: ERROR SOLICITANDO CUENTAS")
            print("ERROR:", e)

        return


    # --------------------------------------------------------
    # RESPUESTA DE LISTA DE CUENTAS
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
                    print("ACCOUNT ID:", ACCOUNT_ID)

            if not cuenta_encontrada:

                print("CTRADER: NO SE ENCONTRO LA CUENTA:", ACCOUNT_ID)
                return

            # ------------------------------------------------
            # AUTENTICAR LA CUENTA
            # ------------------------------------------------

            solicitud_auth_cuenta = ProtoOAAccountAuthReq()

            solicitud_auth_cuenta.ctidTraderAccountId = ACCOUNT_ID
            solicitud_auth_cuenta.accessToken = ACCESS_TOKEN

            print("CTRADER: AUTENTICANDO CUENTA")
            print("ACCOUNT ID:", ACCOUNT_ID)

            client.send(solicitud_auth_cuenta)

        except Exception as e:

            print("CTRADER: ERROR PROCESANDO LISTA DE CUENTAS")
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
        print("ACCOUNT ID:", respuesta.ctidTraderAccountId)
        print("================================")

        print("CTRADER: SOLICITANDO INFORMACION NAS100")

        solicitud_nas100 = ProtoOASymbolByIdReq()
        solicitud_nas100.ctidTraderAccountId = ACCOUNT_ID
        solicitud_nas100.symbolId.append(NAS100_SYMBOL_ID)

        try:
            client.send(solicitud_nas100)
        except Exception as e:
            print("ERROR SOLICITANDO NAS100:", e)

        print("CTRADER: SOLICITANDO INFORMACION XAUUSD")

        solicitud_xau = ProtoOASymbolByIdReq()
        solicitud_xau.ctidTraderAccountId = ACCOUNT_ID
        solicitud_xau.symbolId.append(XAUUSD_SYMBOL_ID)

        try:
            client.send(solicitud_xau)
        except Exception as e:
            print("ERROR SOLICITANDO XAUUSD:", e)

        return


    # --------------------------------------------------------
    # INFORMACION DE SIMBOLOS
    # --------------------------------------------------------

    if message.payloadType == ProtoOASymbolByIdRes().payloadType:

        respuesta = Protobuf.extract(message)

        print("================================")
        print("CTRADER: INFORMACION DE SIMBOLO RECIBIDA")
        print("================================")

        for simbolo in respuesta.symbol:

            print("SYMBOL ID:", simbolo.symbolId)
            print("DIGITS:", simbolo.digits)
            print("PIP POSITION:", simbolo.pipPosition)
            print("LOT SIZE:", simbolo.lotSize)
            print("MIN VOLUME:", simbolo.minVolume)
            print("STEP VOLUME:", simbolo.stepVolume)

            if simbolo.symbolId == NAS100_SYMBOL_ID:
                print("CTRADER: NAS100 CONFIRMADO")
                print("VOLUMEN 0.01 LOTE:", NAS100_VOLUME)

            elif simbolo.symbolId == XAUUSD_SYMBOL_ID:
                print("CTRADER: XAUUSD CONFIRMADO")
                print("VOLUMEN 0.01 LOTE:", XAUUSD_VOLUME)

        return


    # --------------------
```
