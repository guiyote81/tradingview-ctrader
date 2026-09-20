from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
return "Servidor funcionando correctamente"

@app.route("/status")
def status():
return "OK"
