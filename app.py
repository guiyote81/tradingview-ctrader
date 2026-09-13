from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
return "Servidor TradingView cTrader funcionando"

@app.route("/callback")
def callback():
return "Callback cTrader funcionando"

@app.route("/webhook", methods=["POST"])
def webhook():
return "Webhook recibido", 200
