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

__author__ = 'bejar'

app = Flask(__name__)

busquedas = {}
totalbusquedas = 0
clientid = ''
diraddress = ''


@app.route("/message", methods=['GET', 'POST'])
def message():
    """
    Entrypoint para todas las comunicaciones

    :return:
    """
    global busquedas
    

    # if request.form.has_key('message'):
    if 'message' in request.form:
        checkindate = None
        checkoutdate = None
        adults = None
        code = None
        maxflightprice = None
        roomQuantity = None
        radius = None
        minPrice = None
        maxPrice = None
        if 'checkindate' in request.form: checkindate = request.form['checkindate']
        if 'checkoutdate' in request.form: checkoutdate = request.form['checkoutdate']
        if 'adults' in request.form: adults = request.form['adults']
        if 'code' in request.form: code = request.form['code']
        if 'maxflightprice' in request.form: maxflightprice = request.form['maxflightprice']
        if 'roomQuantity' in request.form: roomQuantity = request.form['roomQuantity']
        if 'radius' in request.form: radius = request.form['radius']
        if 'minPrice' in request.form: minPrice = request.form['minPrice']
        if 'maxPrice' in request.form: maxPrice = request.form['maxPrice']

        inicia_busqueda(
            checkindate ,
            checkoutdate,
            adults,
            code,
            maxflightprice,
            roomQuantity,
            radius,
            minPrice,
            maxPrice
        )

        return redirect('/')
    
    else:
        # Respuesta del solver SOLVED|PROBID,SOLUTION
        mess = request.args['message'].split('|')
        if len(mess) == 2:
            messtype, messparam = mess
            if messtype == 'SOLVED':
                solution = messparam.split(',')
                if len(solution) == 2:
                    probid, sol = solution
                    if probid in problems:
                        problems[probid][2] = sol
                    else:  # Para el script de test de stress
                        problems[probid] = ['DUMMY', 'DUMMY', sol]
        return 'OK'

def inicia_busqueda(checkindate, checkoutdate, adults, code, maxflightprice, roomQuantity, radius, minPrice, maxPrice):
    if checkindate is None: checkindate = ''
    if checkoutdate is None: checkoutdate = ''
    if adults is None: adults = ''
    log.info("checkindate = " + checkindate)
    log.info("checkoutdate = " + checkoutdate)
    log.info("adults = " + adults)
    log.info("code = " + code)

    # global diraddress
    # global busquedas
    # global clientid
    # global port
    global totalbusquedas

    busquedaid = f'{clientid}-{totalbusquedas:03}'
    totalbusquedas += 1

    # Enviar petición al Server para recibir la dirección de un Agente de Presentación
    presentadd = requests.get(diraddress + '/message', params={'message': f'SEARCH|PRES'}).text

    if 'OK' in presentadd:

        # Le quitamos el OK de la respuesta
        presentadd = presentadd[4:]

        busquedas[busquedaid] = ['SENDING', checkindate, checkoutdate, adults, code, maxflightprice, roomQuantity, radius, minPrice, maxPrice]
        log.info("presentadd: " + presentadd)

        mess = f'BUSQ|{busquedaid},{checkindate},{checkoutdate},{adults},{code},{maxflightprice},{roomQuantity},{radius},{minPrice},{maxPrice}'
        resp = requests.get(presentadd + '/message', params={'message': mess}).text
        if 'ERROR' not in resp:
            busquedas[busquedaid][0] = 'PENDING' #['PENDING', checkindate, checkoutdate, adults, code, maxflightprice, roomQuantity, radius, minPrice, maxPrice]
        else:
            busquedas[busquedaid][0] = resp #['FAILED PRES', checkindate, checkoutdate, adults, code, maxflightprice, roomQuantity, radius, minPrice, maxPrice]
            # problems[probid] = [probtype, problem, 'FAILED SOLVER']
    # Solver no encontrado
    else:
        busquedas[busquedaid][0] = 'FAILED SERVER' #['FAILED DS', checkindate, checkoutdate, adults, code, maxflightprice, roomQuantity, radius, minPrice, maxPrice]

@app.route('/info')
def info():
    """
    Entrada que da informacion sobre el agente a traves de una pagina web
    """
    global problems

    return render_template('busquedas_usuario.html', busq=busquedas)


@app.route('/')
def renderform():
    """
    Interfaz con el cliente a traves de una pagina de web
    """
    # probtypes = ['ARITH', 'MFREQ']
    return render_template('form_itinerario.html')


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

    # Registramos el solver aritmetico en el servicio de directorio
    clientadd = f'http://{hostaddr}:{port}'
    clientid = hostaddr.split('.')[0] + '-' + str(port)
    agenttype = 'CLIENT'
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
