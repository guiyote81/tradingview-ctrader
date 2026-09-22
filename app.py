import os
from flask import Flask, request
from threading import Thread
from twisted.internet import reactor, ssl
from ctrader_open_api import Client
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

app = Flask(__name__)

# Leemos tus variables de Render
CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")
ACCOUNT_ID = int(os.getenv("CTRADER_ACCOUNT_ID"))

# DEMO = 5035, LIVE = 5032 - cambia esto segun tu cuenta
HOST = "demo.ctraderapi.com" 
PORT = 5035

client = Client(HOST, PORT, ssl_context_factory=ssl.ClientContextFactory)
is_ready = False

def on_connected(_):
    print("Conectado a cTrader API, autenticando app...")
    req = ProtoOAApplicationAuthReq()
    req.clientId = CLIENT_ID
    req.clientSecret = CLIENT_SECRET
    client.send(req)

def on_app_auth(res):
    print("App autenticada, autenticando cuenta...")
    req = ProtoOAAccountAuthReq()
    req.ctidTraderAccountId = ACCOUNT_ID
    req.accessToken = ACCESS_TOKEN
    client.send(req)

def on_account_auth(res):
    global is_ready
    is_ready = True
    print(f"¡CUENTA {ACCOUNT_ID} AUTENTICADA! Lista para tradear.")

def execute_order(data):
    # data viene de TradingView: {"symbol": "EURUSD", "action": "buy", "volume": 1000}
    print(f"Ejecutando: {data}")
    # Aqui va tu logica de ProtoOANewOrderReq
    # ...

def start_reactor():
    client.setConnectedCallback(on_connected)
    client.setMessageReceiver(lambda msg: {
        2100: on_app_auth,
        2102: on_account_auth
    }.get(msg.payloadType, lambda x: None)(msg))
    client.startService()
    reactor.run(installSignalHandlers=0)

@app.route('/webhook', methods=['POST'])
def webhook():
    if not is_ready:
        return {"error": "cTrader no conectado aun, esperando auth"}, 503
    
    data = request.get_json()
    reactor.callFromThread(execute_order, data)
    return {"status": "orden enviada a cTrader"}, 200

@app.route('/')
def home():
    return f"Bot {'READY' if is_ready else 'Conectando...'} Account: {ACCOUNT_ID}"

if __name__ == '__main__':
    Thread(target=start_reactor, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
