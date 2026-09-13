from flask import Flask, request
import os
import requests

app = Flask(__name__)

CLIENT_ID = os.environ.get("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CTRADER_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("CTRADER_REDIRECT_URI")

app.add_url_rule("/", "home", lambda: "Servidor TradingView cTrader funcionando")

exchange_token = lambda code: requests.get(
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

app.add_url_rule(
"/callback",
"callback",
lambda: "No se recibió código de autorización" if not request.args.get("code") else ("Autorización recibida correctamente. Podemos continuar." if exchange_token(request.args.get("code")).ok else "Error al obtener el token de cTrader"),
)

app.add_url_rule(
"/webhook",
"webhook",
lambda: ("Webhook recibido", 200),
methods=["POST"]
)
