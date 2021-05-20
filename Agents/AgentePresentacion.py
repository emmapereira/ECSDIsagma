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

AgentePresentacion = Agent('AgentePresentacion',
                       agn.AgentePresentacion,
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
    reg_obj = agn[AgenteAlojamiento.name + '-Register']
    gmess.add((reg_obj, RDF.type, DSO.Register))
    gmess.add((reg_obj, DSO.Uri, AgenteAlojamiento.uri))
    gmess.add((reg_obj, FOAF.name, Literal(AgenteAlojamiento.name)))
    gmess.add((reg_obj, DSO.Address, Literal(AgenteAlojamiento.address)))
    gmess.add((reg_obj, DSO.AgentType, DSO.HotelsAgent))

    # Lo metemos en un envoltorio FIPA-ACL y lo enviamos
    gr = send_message(
        build_message(gmess, perf=ACL.request,
                      sender=AgenteAlojamiento.uri,
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
    logger.info('Peticion de busqueda de itinerario recibida')

    # Extraemos el mensaje y creamos un grafo con el
    message = request.args['content']
    gm = Graph()
    gm.parse(data=message)

    msgdic = get_message_properties(gm)

    # Comprobamos que sea un mensaje FIPA ACL
    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(), ACL['not-understood'], sender=AgentePresentacion.uri, msgcnt=mss_cnt)
    else:
        # Obtenemos la performativa
        perf = msgdic['performative']

        if perf != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(Graph(), ACL['not-understood'], sender=AgentePresentacion.uri, msgcnt=mss_cnt)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
            # de registro

            # Averiguamos el tipo de la accion
            if 'content' in msgdic:
                content = msgdic['content']
                accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            if accion == ECSDIsagma.peticionBusqueda:
                logger.info("Procesando peticion de búsqueda de itinerario")
                # Eliminar los ACLMessage
                restricciones = gm.objects(content, ECSDIsagma.Restringe)
                restricciones_dict = {}
                for restriccion in restricciones:
                    if gm.value(subject=restriccion, predicate=RDF.type) == ECSDIsagma.RestriccionEsCentrico:
                        escentrico = gm.value(subject=restriccion, predicate=ECSDIsagma.EsCentrico)
                        logger.info('EsCentrico: ' + escentrico)
                        restricciones_dict['incenter'] = escentrico
                    elif gm.value(subject=restriccion, predicate=RDF.type) == ECSDIsagma.RestriccionFechaIda:
                        fechaida = gm.value(subject=restriccion, predicate=ECSDIsagma.FechaIda)
                        logger.info('FechaIda: ' + fechaida)
                        restricciones_dict['date1'] = fechaida
                    elif gm.value(subject=restriccion, predicate=RDF.type) == ECSDIsagma.RestriccionFechaVuelta:
                        fechavuelta = gm.value(subject=restriccion, predicate=ECSDIsagma.FechaVuelta)
                        logger.info('FechaVuelta: ' + fechavuelta)
                        restricciones_dict['date2'] = fechavuelta
                    elif gm.value(subject=restriccion, predicate=RDF.type) == ECSDIsagma.RestriccionRangoPrecioAloj:
                        precio_min_aloj = gm.value(subject=restriccion, predicate=ECSDIsagma.Precio_min)
                        precio_max_aloj = gm.value(subject=restriccion, predicate=ECSDIsagma.Precio_max)
                        if precio_min_aloj:
                            logger.info('Precio minimo alojamiento: ' + precio_min_aloj)
                            restricciones_dict['min_price_housing'] = precio_min_aloj.toPython()
                        if precio_max_aloj:
                            logger.info('Precio maximo alojamiento: ' + precio_max_aloj)
                            restricciones_dict['max_price_housing'] = precio_max_aloj.toPython()
                    elif gm.value(subject=restriccion, predicate=RDF.type) == ECSDIsagma.RestriccionRangoPrecioTrans:
                        precio_min_trans = gm.value(subject=restriccion, predicate=ECSDIsagma.Precio_min)
                        precio_max_trans = gm.value(subject=restriccion, predicate=ECSDIsagma.Precio_max)
                        if precio_min_trans:
                            logger.info('Precio minimo transporte: ' + precio_min_trans)
                            restricciones_dict['min_price_transport'] = precio_min_trans.toPython()
                        if precio_max_trans:
                            logger.info('Precio maximo alojamiento: ' + precio_max_trans)
                            restricciones_dict['max_price_transport'] = precio_max_trans.toPython()
                    elif gm.value(subject=restriccion, predicate=RDF.type) == ECSDIsagma.RestriccionPrecioMaximo:
                        precio_max = gm.value(subject=restriccion, predicate=ECSDIsagma.Precio)
                        logger.info('Precio maximo: ' + precio_max)
                        restricciones_dict['max_price'] = precio_max.toPython()


                #enviar mensaje definir servicio alojamiento
                #pasarle las preferencias?
                alojamiento = get_agent_info(agn.AgenteAlojamiento, DirectoryAgent, AgentePresentacion, get_count())
                gr = send_message(
                    build_message(gr, perf=ACL.request, sender=AgentePresentacion.uri, receiver=alojamiento.uri,
                                  msgcnt=get_count(),
                                  content=content), alojamiento.address)

                #enviar mensaje definir servicio AgenteDesplazamiento
                #pasarle las preferencias?
                desplazamiento = get_agent_info(agn.AgenteDesplazamiento, DirectoryAgent, AgentePresentacion, get_count())
                gr = send_message(
                    build_message(gr, perf=ACL.request, sender=AgentePresentacion.uri, receiver=desplazamiento.uri,
                                  msgcnt=get_count(),
                                  content=content), desplazamiento.address)

                #enviar mensaje guardar preferencias usuario al almacenador
                #pasarle las preferencias?
                almacenador = get_agent_info(agn.AgenteAlmacenamiento, DirectoryAgent, AgentePresentacion, get_count())
                gr = send_message(
                    build_message(gr, perf=ACL.request, sender=AgentePresentacion.uri, receiver=almacenador.uri,
                                  msgcnt=get_count(),
                                  content=content), almacenador.address)

                                  

            else if accion == ECSDIsagma.peticionConfirmarItinerario
                logger.info("Procesando peticion de confirmacion de itinerario")

                for item in gm.subjects(RDF.type, ACL.FipaAclMessage):
                    gm.remove((item, None, None))

                #mostrar el itinerario al agente usuario?


            else if accion == ECSDIsagma.ConfirmacionItinerario
                logger.info("Procesando Confirmacion de itinerario")

                for item in gm.subjects(RDF.type, ACL.FipaAclMessage):
                    gm.remove((item, None, None))

                gr = gm

                #faltan cosas probablemente

                #enviar mensaje a agente alojamiento para pedir datos pago
                alojamiento = get_agent_info(agn.AgenteAlojamiento, DirectoryAgent, AgentePresentacion, get_count())
                gr = send_message(
                    build_message(gr, perf=ACL.request, sender=AgentePresentacion.uri, receiver=alojamiento.uri,
                                  msgcnt=get_count(),
                                  content=content), alojamiento.address)

                #enviar mensaje a agente desplazamiento para pedir datos pago
                desplazamiento = get_agent_info(agn.AgenteDesplazamiento, DirectoryAgent, AgentePresentacion, get_count())
                gr = send_message(
                    build_message(gr, perf=ACL.request, sender=AgentePresentacion.uri, receiver=desplazamiento.uri,
                                  msgcnt=get_count(),
                                  content=content), desplazamiento.address)

                #llamamos al tesorero para que obtenga la info de pago del usuario
                tesorero = get_agent_info(agn.AgenteTesorero, DirectoryAgent, AgentePresentacion, get_count())
                gr = send_message(
                    build_message(gr, perf=ACL.request, sender=AgentePresentacion.uri, receiver=tesorero.uri,
                                  msgcnt=get_count(),
                                  content=content), tesorero.address)

                #si el pago fue correcto, llamamos al almacenador para guardar el itinerario generado
                #pasarle el itinerario?
                almacenador = get_agent_info(agn.AgenteAlmacenamiento, DirectoryAgent, AgentePresentacion, get_count())
                gr = send_message(
                    build_message(gr, perf=ACL.request, sender=AgentePresentacion.uri, receiver=almacenador.uri,
                                  msgcnt=get_count(),
                                  content=content), almacenador.address)


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

#def findItinerario(incenter=None, date1=None, date2=None, min_price_housing=0.0, max_price_housing=sys.float_info.max, min_price_transport=0.0, max_price_transport=sys.float_info.max, gr):



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
