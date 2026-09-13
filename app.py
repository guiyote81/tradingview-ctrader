from flask import Flask, request
import os
import requests

app = Flask(__name__)

CLIENT_ID = os.environ.get("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CTRADER_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("CTRADER_REDIRECT_URI")

app.add_url_rule(
"/",
"home",
lambda: "Servidor TradingView cTrader funcionando"
)

def callback():
code = request.args.get("code")

if not code:
return "No se recibió código de autorización", 400

response = requests.get(
"https://openapi.ctrader.com/apps/token",
params={
"grant_type": "authorization_code",
"code": code,
"redirect_uri": REDIRECT_URI,
"client_id": CLIENT_ID,
"client_secret": CLIENT_SECRET
},
timeout=20
)

data = response.json()

if data.get("errorCode"):
return "Error cTrader: " + str(data), 400

return "Autorización completada correctamente. Ya podemos continuar."

app.add_url_rule("/callback", "callback", callback)

app.add_url_rule(
"/webhook",
"webhook",
lambda: ("Webhook recibido", 200),
methods=["POST"]
)
