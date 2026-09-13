from flask import Flask

app = Flask(__name__)

def home():
return "Servidor TradingView cTrader funcionando"

app.add_url_rule("/", "home", home)

def callback():
return "Callback cTrader funcionando"

app.add_url_rule("/callback", "callback", callback)

def webhook():
return "Webhook recibido", 200

app.add_url_rule("/webhook", "webhook", webhook, methods=["POST"])
