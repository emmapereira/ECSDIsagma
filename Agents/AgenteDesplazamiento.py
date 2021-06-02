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
import threading

from rdflib import Namespace, Graph, Literal
from rdflib.namespace import FOAF, RDF
from flask import Flask

from Utilities.ACL import ACL
from Utilities.FlaskServer import shutdown_server
from Utilities.Agent import Agent
from Utilities.ACLMessages import build_message, send_message, get_message_properties
from Utilities.OntoNamespaces import ECSDIsagma
from Utilities.DSO import DSO
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

AgenteDesplazamiento = Agent('AgenteDesplazamiento',
                       agn.AgenteDesplazamiento,
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

def get_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt

def procesarBusquedaDesplazamiento(grafo, contenido):
    logger.info("Recibida peticion de busqueda de transporte")
    thread1 = threading.Thread(target=registrarBusquedaDesplazamientos,args=(grafo,contenido))
    thread1.start()



#pensar código, registramos nosotros la busqueda de alojamientos? donde?
def registrarBusquedaDesplazamientos(grafo, contenido):
    origen = None
    destino = None
    precio = None
    transporte = None
    for a,b,c in graph:
        if b == ECSDIsagma.Origen:
            origen = c
        elif b == ECSDIsagma.Destino:
            destino = c
        elif b == ECSDIsagma.Precio:
            precio = c
        elif b == ECSDIsagma.Transporte:
            transporte = c

    busquedaTrans = grafo.value(predicate=RDF.type,object=ECSDIsagma.PeticionTransportesDisponibles)
    grafo.add((busquedaTrans))

    logger.info("Registrando la peticion de busqueda")
    # Añadimos el alojamiento a la base de datos de alojamientos
    ontologyFile = open('../data/DesplazamientosDB')

    graph = Graph()
    graph.bind('default', ECSDIsagma)
    graph.parse(ontologyFile, format='turtle')
    #graph += grafo (no se si hace falta)

    sujeto = ECSDI['Transporte' + str(getMessageCount())]
    graph.add((sujeto, RDF.type, ECSDIsagma.Desplazamiento))
    graph.add((sujeto, ECSDIsagma.Origen, Literal(origen, datatype=XSD.string)))
    graph.add((sujeto, ECSDIsagma.Destino, Literal(destino, datatype=XSD.int)))
    graph.add((sujeto, ECSDIsagma.Precio, Literal(precio, datatype=XSD.string)))
    graph.add((sujeto, ECSDIsagma.Transporte, Literal(transporte, datatype=XSD.int)))

    # Guardamos el grafo
    graph.serialize(destination='../data/DesplazamientosDB', format='turtle')
    logger.info("Registro de alojamientos finalizado")

def register_message():
    """
    Envia un mensaje de registro al servicio de registro
    usando una performativa Request y una accion Register del
    servicio de directorio

    :param gmess:
    :return:
    """

    logger.info('Nos registramos')

    global mss_cnt

    gmess = Graph()

    # Construimos el mensaje de registro
    gmess.bind('foaf', FOAF)
    gmess.bind('dso', DSO)
    reg_obj = agn[AgenteDesplazamiento.name + '-Register']
    gmess.add((reg_obj, RDF.type, DSO.Register))
    gmess.add((reg_obj, DSO.Uri, AgenteDesplazamiento.uri))
    gmess.add((reg_obj, FOAF.name, Literal(AgenteDesplazamiento.name)))
    gmess.add((reg_obj, DSO.Address, Literal(AgenteDesplazamiento.address)))
    gmess.add((reg_obj, DSO.AgentType, DSO.HotelsAgent))

    # Lo metemos en un envoltorio FIPA-ACL y lo enviamos
    gr = send_message(
        build_message(gmess, perf=ACL.request,
                      sender=AgenteDesplazamiento.uri,
                      receiver=DirectoryAgent.uri,
                      content=reg_obj,
                      msgcnt=mss_cnt),
        DirectoryAgent.address)
    mss_cnt += 1

    return gr


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
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteDesplazamiento.uri, msgcnt=mss_cnt)
    else:
        # Obtenemos la performativa
        perf = msgdic['performative']

        if perf != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(Graph(), ACL['not-understood'], sender=AgenteDesplazamiento.uri, msgcnt=mss_cnt)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
            # de registro

            # Averiguamos el tipo de la accion
            if 'content' in msgdic:
                content = msgdic['content']
                accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Si la acción es de tipo peticionAlojamientosDisponibles emprendemos las acciones consequentes
            if accion == ECSDIsagma.definir_servicio_desplazamiento:
                logger.info("Procesando peticion de búsqueda de desplazamiento")
                # Eliminar los ACLMessage
                for item in gm.subjects(RDF.type, ACL.FipaAclMessage):
                    gm.remove((item, None, None))

                #deberemos comunicarnos con agentes externos para conseguir lista de alojamientos
                procesarBusquedaAlojamiento(gm, content)

            else if accion == ECSDIsagma.OfertaDesplazamientos
                logger.info("Procesando lista de ofertas de transportes")

                gm.remove((content, None, None))
                for item in gm.subjects(RDF.type, ACL.FipaAclMessage):
                    gm.remove((item, None, None))

                save = None
                for item in gm.subjects(RDF.type, ECSDI.OfertaDesplazamientos):
                    save = item

                #guardar alojamientos en bd alojamientos ?
                ontologyFile = open('../data/desplazamientos')

                g = Graph()
                g.parse(ontologyFile, format='turtle')
                g += gm

                g.serialize(destination='../data/desplazamientos', format='turtle')

            else if accion == ECSDIsagma.PeticionMetodoPago
                logger.info("Procesando peticion del metodo de pago del desplazamiento")

                #comunicarnos con agente externo para conseguir la info de pago del alojamiento
                #confirmar el alojamiento

            else if accion == ECSDIsagma.MetodoPago
                logger.info("Procesando metodo de pago del desplazamiento")

                #devolver el metodo de pago al agente de presentacion?



            # No habia ninguna accion en el mensaje
            else:
                gr = build_message(Graph(),
                                ACL['not-understood'],
                                sender=DirectoryAgent.uri,
                                msgcnt=get_count())


    logger.info('Respondemos a la peticion')
    return gr.serialize(format='xml')
    return serialize, 200


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


def AgenteDesplazamientoBehavior(cola):
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
    ab1 = Process(target=AgenteDesplazamientoBehavior, args=(cola1,))
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')
