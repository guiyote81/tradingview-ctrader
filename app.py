import os
from flask import Flask, request
from threading import Thread
from twisted.internet import reactor
from ctrader_open_api import Client
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *

app = Flask(__name__)

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")
ACCOUNT_ID = int(os.getenv("CTRADER_ACCOUNT_ID", "0"))

HOST = "demo.ctraderapi.com"
PORT = 5035 # usa 5032 si es LIVE

client = Client(HOST, PORT) # <- CORREGIDO, sin ssl_context_factory
is_ready = False

def on_connected(_):
    print("Conectado a cTrader, autenticando app...")
    req = ProtoOAApplicationAuthReq()
    req.clientId = CLIENT_ID
    req.clientSecret = CLIENT_SECRET
    client.send(req)

def on_message(msg):
    global is_ready
    if msg.payloadType == 2101: # App Auth Response
        print("App autenticada OK, autenticando cuenta...")
        req = ProtoOAAccountAuthReq()
        req.ctidTraderAccountId = ACCOUNT_ID
        req.accessToken = ACCESS_TOKEN
        client.send(req)
    elif msg.payloadType == 2103: # Account Auth Response
        is_ready = True
        print(f"¡CUENTA {ACCOUNT_ID} AUTENTICADA! Lista para tradear.")
    else:
        print(f"Mensaje recibido: {msg.payloadType}")

def execute_order(data):
    print(f"EJECUTANDO ORDEN REAL: {data}")
    # acá va tu lógica de NewOrder

def start_reactor():
    print("INICIANDO CTRADER")
    client.setConnectedCallback(on_connected)
    client.setMessageReceiver(on_message)
    client.startService()
    reactor.run(installSignalHandlers=0)

@app.route('/webhook', methods=['POST'])
def webhook():
    if not is_ready:
        print("Webhook recibido pero cTrader aun no listo")
        return {"error": "cTrader no listo"}, 503
    data = request.get_json()
    reactor.callFromThread(execute_order, data)
    return {"status": "ok"}, 200

@app.route('/')
def home():
    return f"Bot {'READY' if is_ready else 'Conectando...'} Account: {ACCOUNT_ID}"

if __name__ == '__main__':
    Thread(target=start_reactor, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
