from flask import Flask

app = Flask(__name__)

app.add_url_rule(
"/",
"home",
lambda: "Servidor funcionando correctamente"
)

app.add_url_rule(
"/status",
"status",
lambda: "OK"
)
