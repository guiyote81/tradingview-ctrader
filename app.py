from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def home():
return "Servidor TradingView - cTrader funcionando."

@app.route("/callback")
def callback():
code = request.args.get("code")

if code:
return f"""
<h2>Autorización recibida correctamente</h2>
<p>El servidor recibió el código de cTrader.</p>
"""

return """
<h2>Callback de cTrader</h2>
<p>No se recibió ningún código de autorización.</p>
"""

@app.route("/webhook", methods=["POST"])
def webhook():
data = request.get_json(silent=True)

print("Alerta recibida:", data)

return {
"status": "received",
"data": data
}, 200
