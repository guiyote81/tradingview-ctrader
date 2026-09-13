from flask import Flask

app = Flask(__name__)

app.add_url_rule("/", "home", lambda: "Servidor TradingView cTrader funcionando")
app.add_url_rule("/callback", "callback", lambda: "Callback cTrader funcionando")
app.add_url_rule("/webhook", "webhook", lambda: ("Webhook recibido", 200), methods=["POST"])
