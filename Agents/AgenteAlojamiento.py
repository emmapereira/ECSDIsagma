# -*- coding: utf-8 -*-
"""
Agente usando los servicios web de Flask
/comm es la entrada para la recepcion de mensajes del agente
/Stop es la entrada que para el agente
Tiene una funcion AgenteAlojamientoBehavior que se lanza como un thread concurrente
Asume que el agente de registro esta en el puerto 9000

"""

from multiprocessing import Process, Queue
import socket
import argparse

from rdflib import Namespace, Graph
from flask import Flask
from Utilities.FlaskServer import shutdown_server
from Utilities.Agent import Agent
from Utilities.OntoNamespaces import ECSDIsagma
from Utilities.Logging import config_logger

__author__ = 'sagma'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--open', help="Define si el servidor esta abierto al exterior o no", action='store_true',
                    default=False)
parser.add_argument('--verbose', help="Genera un log de la comunicacion del servidor web", action='store_true',
                        default=False)
parser.add_argument('--port', type=int, help="Puerto de comunicacion del agente")
parser.add_argument('--dhost', help="Host del agente de directorio")
parser.add_argument('--dport', type=int, help="Puerto de comunicacion del agente de directorio")

# Logging
logger = config_logger(level=1)

# parsing de los parametros de la linea de comandos
args = parser.parse_args()

# Configuration stuff
if args.port is None:
    port = 9001
else:
    port = args.port

if args.open:
    hostname = '0.0.0.0'
    hostaddr = gethostname()
else:
    hostaddr = hostname = socket.gethostname()

print('DS Hostname =', hostaddr)

if args.dport is None:
    dport = 9000
else:
    dport = args.dport

if args.dhost is None:
    dhostname = socket.gethostname()
else:
    dhostname = args.dhost



# AGENT ATTRIBUTES

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgenteAlojamiento = Agent('AgenteAlojamiento',
                       agn.AgenteAlojamiento,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/Register' % hostname,
                       'http://%s:9000/Stop' % hostname)

# Global triplestore graph
dsgraph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)

def procesarBusquedaAlojamiento(grafo, contenido):
    logger.info("Recibida peticion de busqueda de alojamientos")
    thread1 = threading.Thread(target=registrarBusquedaAlojamientos,args=(grafo,contenido))
    thread1.start()
    #thread2 = threading.Thread(target=solicitarBusquedaAlojamientos,args=(grafo,contenido))??
    #thread2.start()??



#pensar código, registramos nosotros la busqueda de alojamientos? donde? mirar github GestorExternoAgent
def registrarBusquedaAlojamientos(grafo, contenido):
    busquedaAloj = grafo.value(predicate=RDF.type,object=ECSDIsagma.PeticionAlojamientosDisponibles)
    grafo.add((busquedaAloj))
    # prioridad = grafo.value(subject=contenido, predicate=ECSDI.Prioridad)
    # fecha = datetime.now() # + timedelta(days=int(prioridad))
    # grafo.add((busquedaAloj,ECSDIsagma.FechaEntrega,Literal(fecha, datatype=XSD.date)))
    logger.info("Registrando la peticion de busqueda")
    ontologyFile = open('../data/AlojamientosDB')

    graph = Graph()
    graph.bind('default', ECSDIsagma)
    graph.parse(ontologyFile, format='turtle')
    #graph += grafo (no se si hace falta)

    #aqui hace cosas para cada atributo de su producto externo, igual podiamos hacerlo con atributos de un alojamiento?
    #sujeto = ECSDI['ProductoExterno' + str(getMessageCount())]
    #graph.add((sujeto, RDF.type, ECSDI.ProductoExterno))
    #graph.add((sujeto, ECSDI.Nombre, Literal(nombre, datatype=XSD.string)))
    #graph.add((sujeto, ECSDI.Precio, Literal(precio, datatype=XSD.float)))
    #graph.add((sujeto, ECSDI.Descripcion, Literal(descripcion, datatype=XSD.string)))


    # Guardamos el grafo
    grafoEnvios.serialize(destination='../data/AlojamientosDB', format='turtle')
    logger.info("Registro de alojamientos finalizado")


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion del agente
    Simplemente retorna un objeto fijo que representa una
    respuesta a una busqueda de alojamientos

    Asumimos que se reciben siempre acciones que se refieren a lo que puede hacer
    el agente (buscar con ciertas preferencias)
    Las acciones se mandan siempre con un Request
    Prodriamos resolver las busquedas usando una performativa de Query-ref??????????????
    """
    global dsgraph
    global mss_cnt
    logger.info('Peticion de busqueda de alojamiento recibida')

    # Extraemos el mensaje y creamos un grafo con el
    message = request.args['content']
    gm = Graph()
    gm.parse(data=message)

    msgdic = get_message_properties(gm)

    # Comprobamos que sea un mensaje FIPA ACL
    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteAlojamiento.uri, msgcnt=mss_cnt)
    else:
        # Obtenemos la performativa
        perf = msgdic['performative']

        if perf != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(Graph(), ACL['not-understood'], sender=AgenteAlojamiento.uri, msgcnt=mss_cnt)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
            # de registro

            # Averiguamos el tipo de la accion
            if 'content' in msgdic:
                content = msgdic['content']
                accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Si la acción es de tipo peticionAlojamientosDisponibles emprendemos las acciones consequentes
            if accion == ECSDIsagma.peticionAlojamientosDisponibles:
                logger.info("Procesando peticion de búsqueda de alojamiento")
                # Eliminar los ACLMessage
                for item in gm.subjects(RDF.type, ACL.FipaAclMessage):
                    gm.remove((item, None, None))

                procesarBusquedaAlojamiento(gm, content)

            # Por ahora simplemente retornamos un Inform-done
            gr = build_message(Graph(),
                               ACL['inform'],
                               sender=InfoAgent.uri,
                               msgcnt=mss_cnt,
                               receiver=msgdic['sender'], )

    mss_cnt += 1

    logger.info('Respondemos a la peticion')

    return gr.serialize(format='xml')


@app.route("/Stop")
def stop():
    """
    Entrypoint que para el agente

    :return:
    """
    tidyup()
    shutdown_server()
    return "Parando Servidor"


def tidyup():
    """
    Acciones previas a parar el agente

    """
    global cola1
    cola1.put(0)


def AgenteAlojamientoBehavior(cola):
    """
    Un comportamiento del agente

    :return:
    """
    # Registramos el agente
    gr = register_message()

    # Escuchando la cola hasta que llegue un 0
    fin = False
    while not fin:
        while cola.empty():
            pass
        v = cola.get()
        if v == 0:
            fin = True
        else:
            print(v)


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=AgenteAlojamientoBehavior, args=(cola1,))
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')
