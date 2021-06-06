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

pagos = {}
totalpagos = 0
clientid = ''
diraddress = ''

@app.route("/message", methods=['GET', 'POST'])
def message():
    """
    Entrypoint para todas las comunicaciones

    :return:
    """
    global totalpagos
    global pagos

    mess = request.args['message']

    if '|' not in mess:
        return 'ERROR: INVALID MESSAGE'
    else:
        log.info('Recibo mensaje')
        # Sintaxis de los mensajes "TIPO|PARAMETROS"
        mess = mess.split('|')
        if len(mess) != 2:
            log.info('ERROR: INVALID MESSAGE')
            return 'ERROR: INVALID MESSAGE'
        else:
            messtype, messparam = mess

        if messtype not in ['PAY']:
            log.info('ERROR: INVALID REQUEST')
            return 'ERROR: INVALID REQUEST'
        else:
            # parametros mensaje SOLVE = "PROBTYPE,CLIENTADDRESS,PROBID,PROB"
            if messtype == 'PAY':
                log.info('Recibo petición de pago')
                param = messparam.split(',')
                if len(param) == 2:
                    log.info('Los parámetros están guays')
                    name, iban = param
                    pagoid = totalpagos
                    totalpagos += 1
                    pagos[pagoid] = ['PENDING', name, iban]
                    
                    # Hace cosas

                    pagos[pagoid] = ['SAVING', name, iban]
                    guardarInfoPago(name, iban)

                    pagos[pagoid][0] = 'DONE'
                    
                    return "{},{}".format(name, iban)
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


def guardarInfoPago(name, iban):
    DBpagos = open("DB/infopago.txt", "a+")

    DBpagos.write("[Nombre]: {}\n".format(name))
    DBpagos.write("[IBAN]: {}\n".format(iban))
    DBpagos.write("\n")

    DBpagos.close()


@app.route('/info')
def info():
    """
    Entrada que da informacion sobre el agente a traves de una pagina web
    """
    global problems

    return render_template('busquedas_alojamiento.html', busq=pagos)


@app.route("/stop")
def stop():
    """
    Entrada que para el agente
    """
    shutdown_server()
    return "Parando Servidor"


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

    # Registramos el solver aritmetico en el servicio de directorio
    clientadd = f'http://{hostaddr}:{port}'
    clientid = hostaddr.split('.')[0] + '-' + str(port)
    agenttype = 'TESOR'
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
