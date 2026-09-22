from ctrader_open_api import Client, TcpProtocol, EndPoints
from twisted.internet import reactor


print("================================")
print("PRUEBA DE CONEXION CTRADER")
print("================================")

try:

    print("CREANDO CLIENTE...")

    client = Client(
        EndPoints.PROTOBUF_DEMO_HOST,
        EndPoints.PROTOBUF_PORT,
        TcpProtocol
    )

    print("CLIENTE CREADO")
    print("INTENTANDO CONECTAR...")

    def conectado(client_instance):

        print("================================")
        print("CTRADER CONECTADO")
        print("================================")

    def desconectado(client_instance, reason):

        print("================================")
        print("CTRADER DESCONECTADO")
        print("RAZON:", reason)
        print("================================")

    client.setConnectedCallback(conectado)
    client.setDisconnectedCallback(desconectado)

    print("INICIANDO SERVICIO...")

    client.startService()

    print("SERVICIO INICIADO")
    print("ESPERANDO CONEXION...")

    reactor.run(
        installSignalHandlers=0
    )

except Exception as e:

    print("================================")
    print("ERROR")
    print(type(e).__name__)
    print(repr(e))
    print("================================")
