import os
import re
import threading
import time
import queue
from flask import Flask, request, jsonify
from ctrader_open_api import Client, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq, ProtoOAAccountAuthReq, ProtoOANewOrderReq,
)
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import (
    ProtoOAOrderType, ProtoOATradeSide,
)
from twisted.internet import reactor

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("CTRADER_ACCESS_TOKEN")
ACCOUNT_ID = int(os.getenv("CTRADER_ACCOUNT_ID", "48481130"))

SYMBOLS = {
    "XAUUSD": {"id": 41, "volume": 1000},
    "GOLD": {"id": 41, "volume": 1000},
    "NAS100": {"id": 10014, "volume": 1000},
    "NASDAQ": {"id": 10014, "volume": 1000},
}

app = Flask(__name__)
order_queue = queue.Queue()
status = {"conectado": False, "app_auth": False, "acc_auth": False}

def interpretar_alerta(message):
    texto = message.upper().strip()
    side = "BUY" if "COMPRA" in texto or "BUY" in texto else "SELL" if "VENTA" in texto or "SELL" in texto else None
    if not side: return None
    symbol = None
    for k in SYMBOLS:
        if k in texto:
            symbol = k; break
    if not symbol: return None
    if symbol == "GOLD": symbol = "XAUUSD"
    if symbol in ("NASDAQ",): symbol = "NAS100"
    sl = None; tp = None
    m_sl = re.search(r"SL[\s:=]+([0-9.]+)", texto)
    m_tp = re.search(r"TP[\s:=]+([0-9.]+)", texto)
    if m_sl: sl = float(m_sl.group(1))
    if m_tp: tp = float(m_tp.group(1))
    return {"symbol": symbol, "side": side, "sl": sl, "tp": tp}

def run_ctrader():
    global client
    client = Client(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)
 def on_connected(client_instance):
        status["conectado"] = True
        req = ProtoOAApplicationAuthReq(); req.clientId = CLIENT_ID; req.clientSecret = CLIENT_SECRET
        client.send(req)
    def on_message(client_instance, msg):
        try:
            pType = getattr(msg, "payloadType", None)
            if pType == 2100:
                status["app_auth"] = True
                acc = ProtoOAAccountAuthReq(); acc.ctidTraderAccountId = ACCOUNT_ID; acc.accessToken = ACCESS_TOKEN
                client.send(acc)
            if hasattr(msg.payload, "ctidTraderAccountId") and msg.payload.ctidTraderAccountId == ACCOUNT_ID:
                if status["app_auth"]: status["acc_auth"] = True; print("LISTO PARA OPERAR")
        except: pass
def on_disconnected(client_instance, reason):
        status["conectado"]=False; status["app_auth"]=False; status["acc_auth"]=False
        time.sleep(5)
        try: client.startService()
        except: pass
    def check_queue():
        while not order_queue.empty():
            if not status["acc_auth"]: break
            order = order_queue.get()
            cfg = SYMBOLS.get(order["symbol"])
            req = ProtoOANewOrderReq()
            req.ctidTraderAccountId = ACCOUNT_ID; req.symbolId = cfg["id"]
            req.orderType = ProtoOAOrderType.MARKET
            req.tradeSide = ProtoOATradeSide.BUY if order["side"]=="BUY" else ProtoOATradeSide.SELL
            req.volume = cfg["volume"]
            if order.get("sl"): req.stopLoss = order["sl"]
            if order.get("tp"): req.takeProfit = order["tp"]
            client.send(req)
            print(f"ORDEN ENVIADA {order}")
    client.setConnectedCallback(on_connected); client.setMessageReceivedCallback(on_message); client.setDisconnectedCallback(on_disconnected)
    client.startService()
    def loop():
        while True: check_queue(); time.sleep(0.5)
    threading.Thread(target=loop, daemon=True).start()
    if not reactor.running: reactor.run(installSignalHandlers=0)

threading.Thread(target=run_ctrader, daemon=True).start()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    msg = (data.get("message") if data else None) or request.data.decode("utf-8", errors="ignore")
    parsed = interpretar_alerta(msg)
    if not parsed: return jsonify({"status": "error"}), 400
    order_queue.put(parsed)
    return jsonify({"status": "ok", "order": parsed}), 200

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "ctrader": status})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
