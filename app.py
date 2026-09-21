import os
import threading
import time

from flask import Flask, request

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiMessages_pb2 import *

app = Flask(**name**)

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

def abrir_operacion(simbolo, direccion):

```
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
```

def procesar_alerta(mensaje):

```
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
```

def mensaje_recibido(client, message):

```
global cuenta_autenticada

print("================================")
print("CTRADER: MENSAJE RECIBIDO")

try:
    print("PAYLOAD TYPE:", message.payloadType)
except Exception:
    pass

print("================================")


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


if message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:

    print("CTRADER: LISTA DE CUENTAS RECIBIDA")

    respuesta = Protobuf.extract(message)

    try:

        cantidad = len(respuesta.ctidTraderAccount)

        print("CTRADER: CANTIDAD DE CUENTAS:", cantidad)

        cuenta_encontrada = False

        for cuenta in respuesta.ctidTraderAccount:

            print("--------------------------------")
            print("ACCOU
```
