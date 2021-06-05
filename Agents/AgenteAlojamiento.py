"""
.. module:: Client

Client
*************

:Description: Client

    Cliente del resolvedor distribuido

:Authors: bejar
    

:Version: 

:Created on: 06/02/2018 8:21 

"""

from Util import gethostname
import argparse
from Utilities.FlaskServer import shutdown_server
import requests
from flask import Flask, request, render_template, url_for, redirect
import logging
import socket
from amadeus import Client, ResponseError

__author__ = 'sagma'

app = Flask(__name__)

busquedas = {}
totalbusquedas = 0
clientid = ''
diraddress = ''

amadeus = Client(
    client_id='Gu3svGYecxv4aPs2fusVIEloak3YSVxU',
    client_secret='aektZUqvk4SbaZns'
    )

def encontrarAloj(checkindate, checkoutdate, adults, roomQuantity, radius, minPrice, maxPrice):
    try:
        response = amadeus.shopping.hotel_offers.get(
            cityCode = 'BCN',
            radius=radius,
            radiusUnit = 'KM',
            checkInDate = checkindate,
            checkOutDate = checkoutdate,
            roomQuantity = roomQuantity,
            adults = adults,
            priceRange = minPrice + '-' + maxPrice,
            currency = 'EUR'
            )
        
        log.info('Hey el amadeus ha respodido eh')

        return response.data[0]
    except ResponseError as error:
        log.error("amadeus fucked up")
        return error

@app.route("/message", methods=['GET', 'POST'])
def message():
    """
    Entrypoint para todas las comunicaciones

    :return:
    """
    global problems

    mess = request.args['message']

    if '|' not in mess:
        return 'ERROR: INVALID MESSAGE'
    else:
        log.info('Recibo mensaje')
        # Sintaxis de los mensajes "TIPO|PARAMETROS"
        mess = mess.split('|')
        if len(mess) != 2:
            return 'ERROR: INVALID MESSAGE'
        else:
            messtype, messparam = mess

        if messtype not in ['BUSQALOJ']:
            return 'ERROR: INVALID REQUEST'
        else:
            # parametros mensaje SOLVE = "PROBTYPE,CLIENTADDRESS,PROBID,PROB"
            if messtype == 'BUSQALOJ':
                log.info('Recibo petición de búsqueda de alojamiento')
                param = messparam.split(',')
                if len(param) == 8:
                    log.info('Los parámetros están guays')
                    busquedaid, checkindate, checkoutdate, adults, roomQuantity, radius, minPrice, maxPrice = param
                    busquedas[busquedaid] = ['PENDING', checkindate, checkoutdate, adults, roomQuantity, radius, minPrice, maxPrice]
                    
                    alojs = encontrarAloj(checkindate, checkoutdate, adults, roomQuantity, radius, minPrice, maxPrice)
                    log.info(alojs)
                else:
                    log.error('WRONG PARAMETERS')
                    return 'ERROR: WRONG PARAMETERS'
            # respuesta del solver con una solucion
            elif messtype == 'SOLVED':
                solution = messparam.split(',')
                if len(solution) == 2:
                    probid, sol = solution
                    if probid in problems:
                        problems[probid][3] = 'SOLVED'
                        resp = requests.get(problems[probid][1] + '/message',
                                            params={'message': f'SOLVED|{probid},{sol}'}).text
                    return 'OK'
                return 'OK'
    return ''


@app.route('/info')
def info():
    """
    Entrada que da informacion sobre el agente a traves de una pagina web
    """
    global problems

    return render_template('busquedas_alojamiento.html', busq=busquedas)


@app.route("/stop")
def stop():
    """
    Entrada que para el agente
    """
    shutdown_server()
    return "Parando Servidor"


# def send_message(probtype, problem):
#     """
#     Envia un request a un solver

#     mensaje:

#     SOLVE|TYPE,PROBLEM,PROBID,CLIENTID

#     :param probid:
#     :param probtype:
#     :param proble:
#     :return:
#     """
#     global probcounter
#     global clientid
#     global diraddress
#     global port
#     global problems

#     probid = f'{clientid}-{probcounter:03}'
#     probcounter += 1

#     # Busca un sotver en el servicio de directorio
#     solveradd = requests.get(diraddress + '/message', params={'message': f'SEARCH|SOLVER'}).text
#     # Solver encontrado
#     if 'OK' in solveradd:
#         # Le quitamos el OK de la respuesta
#         solveradd = solveradd[4:]

#         problems[probid] = [probtype, problem, 'PENDING']
#         mess = f'SOLVE|{probtype},{clientadd},{probid},{sanitize(problem)}'
#         resp = requests.get(solveradd + '/message', params={'message': mess}).text
#         if 'ERROR' not in resp:
#             problems[probid] = [probtype, problem, 'PENDING']
#         else:
#             problems[probid] = [probtype, problem, 'FAILED SOLVER']
#     # Solver no encontrado
#     else:
#         problems[probid] = (probtype, problem, 'FAILED DS')


# def sanitize(prob):
#     """
#     remove problematic punctuation signs from the string of the problem
#     :param prob:
#     :return:
#     """
#     return prob.replace(',', '*')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--open', help="Define si el servidor esta abierto al exterior o no", action='store_true',
                        default=False)
    parser.add_argument('--verbose', help="Genera un log de la comunicacion del servidor web", action='store_true',
                        default=False)
    parser.add_argument('--port', default=None, type=int, help="Puerto de comunicacion del agente")
    parser.add_argument('--dir', default=None, help="Direccion del servicio de directorio")

    # parsing de los parametros de la linea de comandos
    args = parser.parse_args()
    log = logging.getLogger('werkzeug')
    if not args.verbose:
        log.setLevel(logging.ERROR)

    # Configuration stuff
    if args.port is None:
        port = 9001
    else:
        port = args.port

    if args.open:
        hostname = '0.0.0.0'
        hostaddr = socket.gethostname()
    else:
        hostaddr = hostname = socket.gethostname()

    print('DS Hostname =', hostaddr)

    if args.dir is None:
        raise NameError('A Directory Service addess is needed')
    else:
        diraddress = args.dir

    # Registramos el alojamiento en el servicio de directorio
    clientadd = f'http://{hostaddr}:{port}'
    clientid = hostaddr.split('.')[0] + '-' + str(port)
    agenttype = 'ALOJ'
    mess = f'REGISTER|{clientid},{agenttype},{clientadd}'

    done = False
    while not done:
        try:
            resp = requests.get(diraddress + '/message', params={'message': mess}).text
            done = True
        except ConnectionError:
            pass

    if 'OK' in resp:
        print(f'{agenttype} {clientid} successfully registered')
        # Ponemos en marcha el servidor Flask
        app.run(host=hostname, port=port, debug=False, use_reloader=False)

        mess = f'UNREGISTER|{clientid}'
        requests.get(diraddress + '/message', params={'message': mess})
    else:
        print('Unable to register')
