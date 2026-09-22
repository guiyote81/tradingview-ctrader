import os
import re
import multiprocessing

from flask import Flask, request, jsonify

from ctrader_open_api import Client, TcpProtocol, EndPoints

from ctrader_open_api.messages.OpenApiMessages_pb2 import (
ProtoOAApplicationAuthReq,
ProtoOAAccountAuthReq,
ProtoOANewOrderReq,
)

from ctrader_open_api.messages.OpenApiModelMessages_pb2 import (
ProtoOAOrderType,
ProtoOATradeSide,
)

from twisted.internet import reactor
from twisted.internet.task import LoopingCall

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")

ACCOUNT_ID = 48481130

SYMBOL_XAUUSD = 41
SYMBOL_NAS100 = 10014

VOLUME_XAUUSD = 1000
VOLUME_NAS100 = 1000

app = Flask(name)

order_queue = multiprocessing.Queue()

manager = multiprocessing.Manager()

ctrader_status = manager.dict()

ctrader_status["cliente_creado"] = False
ctrader_status["conectado"] = False
ctrader_status["aplicacion_autenticada"] = False
ctrader_status["cuenta_autenticada"] = False

def obtener_configuracion_simbolo(symbol):

symbol = symbol.upper()

if symbol == "XAUUSD":
    return {
        "symbol_id": SYMBOL_XAUUSD,
        "volume": VOLUME_XAUUSD
    }

if symbol in ("NAS100", "NASDAQ", "NASDAQ100"):
    return {
        "symbol_id": SYMBOL_NAS100,
        "volume": VOLUME_NAS100
    }

return None

def interpretar_alerta(message):

if not message:
    return None

texto = message.upper().strip()

if "COMPRA" in texto:
    side = "BUY"

elif "VENTA" in texto:
    side = "SELL"

else:
    return None

if "XAUUSD" in texto:
    symbol = "XAUUSD"

elif "NAS100" in texto:
    symbol = "NAS100"

elif "NASDAQ" in texto:
    symbol = "NAS100"

else:
    return None

match = re.search(
    r"CONFIRMACI[ÓO]N\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",
    texto
)

if not match:
    match = re.search(
        r"([0-9]+(?:[.,][0-9]+)?)",
        texto
    )

if not match:
    return None

precio_texto = match.group(1).replace(",", ".")

try:
    price = float(precio_texto)

except ValueError:
    return None

return {
    "symbol": symbol,
    "side": side,
    "price": price
}

def ctrader_process(order_queue, status):

print("INICIANDO CTRADER")
print("=================================")

print("CTRADER: VARIABLES")
print("CLIENT ID PRESENTE:", bool(CLIENT_ID))
print("CLIENT SECRET PRESENTE:", bool(CLIENT_SECRET))
print("ACCESS TOKEN PRESENTE:", bool(ACCESS_TOKEN))
print("CUENTA:", ACCOUNT_ID)

if not CLIENT_ID or not CLIENT_SECRET or not ACCESS_TOKEN:

    print("CTRADER: FALTAN VARIABLES DE ENTORNO")

    return

print("CTRADER: CREANDO CLIENTE DEMO")

try:

    client = Client(
        EndPoints.PROTOBUF_DEMO_HOST,
        EndPoints.PROTOBUF_PORT,
        TcpProtocol
    )

    status["cliente_creado"] = True

    print("CTRADER: CLIENTE CREADO")

except Exception as e:

    print("CTRADER: ERROR CREANDO CLIENTE")
    print(str(e))

    return


def on_connected():

    print("CTRADER: CONECTADO")

    status["conectado"] = True

    try:

        auth_request = ProtoOAApplicationAuthReq()

        auth_request.clientId = CLIENT_ID
        auth_request.clientSecret = CLIENT_SECRET

        print("CTRADER: AUTENTICANDO APLICACION")

        client.send(auth_request)

    except Exception as e:

        print("CTRADER: ERROR AUTENTICANDO APLICACION")
        print(str(e))


def on_message_received(client_instance, message):

    print("CTRADER: MENSAJE RECIBIDO")

    try:

        payload_type = getattr(message, "payloadType", None)

        if payload_type == ProtoOAApplicationAuthReq().payloadType:

            print("CTRADER: APLICACION AUTENTICADA")

            status["aplicacion_autenticada"] = True

            account_auth = ProtoOAAccountAuthReq()

            account_auth.ctidTraderAccountId = ACCOUNT_ID
            account_auth.accessToken = ACCESS_TOKEN

            print("CTRADER: AUTENTICANDO CUENTA")
            print("CUENTA:", ACCOUNT_ID)

            client.send(account_auth)

            return

    except Exception as e:

        print("CTRADER: ERROR EN AUTENTICACION")
        print(str(e))


    try:

        payload = getattr(message, "payload", None)

        if payload is not None:

            account_id = getattr(
                payload,
                "ctidTraderAccountId",
                None
            )

            if account_id == ACCOUNT_ID:

                status["cuenta_autenticada"] = True

                print(
                    "ctidTraderAccountId:",
                    ACCOUNT_ID
                )

                print("CTRADER: CUENTA AUTENTICADA")
                print("CUENTA:", ACCOUNT_ID)
                print("CTRADER: CLIENTE LISTO PARA OPERAR")

    except Exception as e:

        print("CTRADER: ERROR PROCESANDO MENSAJE")
        print(str(e))


def on_error(error):

    print("CTRADER: ERROR")
    print(error)


def on_disconnected():

    print("CTRADER: DESCONECTADO")

    status["conectado"] = False
    status["aplicacion_autenticada"] = False
    status["cuenta_autenticada"] = False


client.setConnectedCallback(on_connected)

client.setMessageReceivedCallback(
    on_message_received
)

client.setDisconnectedCallback(
    on_disconnected
)

client.setErrorCallback(
    on_error
)

print("CTRADER: CALLBACKS CONFIGURADOS")

def enviar_orden(order):

    symbol = order["symbol"]
    side = order["side"]
    price = order["price"]

    config = obtener_configuracion_simbolo(symbol)

    if not config:

        print("CTRADER: SIMBOLO NO CONFIGURADO")
        print(symbol)

        return

    symbol_id = config["symbol_id"]
    volume = config["volume"]

    if side == "BUY":

        trade_side = ProtoOATradeSide.BUY

    else:

        trade_side = ProtoOATradeSide.SELL

    print("CTRADER: ORDEN RECIBIDA")
    print("SIMBOLO:", symbol)
    print("SYMBOL ID:", symbol_id)
    print("LADO:", side)
    print("PRECIO ALERTA:", price)
    print("VOLUMEN:", volume)

    try:

        request_message = ProtoOANewOrderReq()

        request_message.ctidTraderAccountId = ACCOUNT_ID
        request_message.symbolId = symbol_id
        request_message.orderType = ProtoOAOrderType.MARKET
        request_message.tradeSide = trade_side
        request_message.volume = volume

        print("CTRADER: ENVIANDO ORDEN MARKET")

        client.send(request_message)

        print("CTRADER: ORDEN ENVIADA")

    except Exception as e:

        print("CTRADER: ERROR ENVIANDO ORDEN")
        print(str(e))


def revisar_cola():

    try:

        while True:

            try:

                order = order_queue.get_nowait()

            except Exception:

                break

            print("CTRADER: ORDEN SACADA DE LA COLA")

            if not status["conectado"]:

                print("CTRADER: TODAVIA NO CONECTADO")

                order_queue.put(order)

                break

            if not status["aplicacion_autenticada"]:

                print("CTRADER: APLICACION TODAVIA NO AUTENTICADA")

                order_queue.put(order)

                break

            if not status["cuenta_autenticada"]:

                print("CTRADER: CUENTA TODAVIA NO AUTENTICADA")

                order_queue.put(order)

                break

            enviar_orden(order)

    except Exception as e:

        print("CTRADER: ERROR REVISANDO COLA")
        print(str(e))


print("CTRADER: INICIANDO SERVICIO")

try:

    client.startService()

    print("CTRADER: SERVICIO INICIADO")

except Exception as e:

    print("CTRADER: ERROR INICIANDO SERVICIO")
    print(str(e))

    return


try:

    LoopingCall(revisar_cola).start(0.5)

except Exception as e:

    print("CTRADER: ERROR INICIANDO COLA")
    print(str(e))


print("CTRADER: INICIANDO REACTOR")

try:

    reactor.run()

except Exception as e:

    print("CTRADER: ERROR EN REACTOR")
    print(str(e))

@app.route("/webhook", methods=["POST"])
def webhook():

print("WEBHOOK RECIBIDO")
print("=================================")

try:

    data = request.get_json(silent=True)

    if data and isinstance(data, dict):

        message = (
            data.get("message")
            or data.get("text")
            or data.get("alert")
            or ""
        )

    else:

        message = request.data.decode(
            "utf-8",
            errors="ignore"
        )

except Exception:

    message = request.data.decode(
        "utf-8",
        errors="ignore"
    )


print("Mensaje recibido:", message)

parsed = interpretar_alerta(message)

if not parsed:

    print("CTRADER: ALERTA NO RECONOCIDA")

    return jsonify({
        "status": "error",
        "message": "Alerta no reconocida"
    }), 400


if parsed["side"] == "BUY":

    print(
        "CTRADER: ALERTA",
        parsed["symbol"],
        "BUY"
    )

else:

    print(
        "CTRADER: ALERTA",
        parsed["symbol"],
        "SELL"
    )

print("PRECIO:", parsed["price"])


try:

    order_queue.put(parsed)

    print("CTRADER: ORDEN ENVIADA A LA COLA")

except Exception as e:

    print("CTRADER: ERROR ENVIANDO A LA COLA")
    print(str(e))

    return jsonify({
        "status": "error",
        "message": "No se pudo enviar la orden"
    }), 500


return jsonify({
    "status": "ok",
    "message": "Alerta recibida y enviada a cTrader",
    "symbol": parsed["symbol"],
    "side": parsed["side"],
    "price": parsed["price"]
}), 200

@app.route("/", methods=["GET"])
def home():

return jsonify({
    "status": "online",
    "ctrader_cliente_creado": bool(
        ctrader_status["cliente_creado"]
    ),
    "ctrader_conectado": bool(
        ctrader_status["conectado"]
    ),
    "ctrader_aplicacion_autenticada": bool(
        ctrader_status["aplicacion_autenticada"]
    ),
    "ctrader_cuenta_autenticada": bool(
        ctrader_status["cuenta_autenticada"]
    ),
    "account_id": ACCOUNT_ID
})

ctrader_process_instance = multiprocessing.Process(
target=ctrader_process,
args=(order_queue, ctrader_status),
daemon=True
)

ctrader_process_instance.start()
