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

from os import name
from Util import gethostname
import argparse
from Utilities.FlaskServer import shutdown_server
import requests
from flask import Flask, request, render_template, url_for, redirect, session
import logging
import socket
import ast

__author__ = 'bejar'

app = Flask(__name__)

busquedas = {}
totalbusquedas = 0
clientid = ''
diraddress = ''

def guardarPreferencias(checkindate,checkoutdate,adults,code,maxflightprice,roomQuantity,radius,minPrice,maxPrice):
    
    DBusuarios=open("DB/usuarios.txt","a+")

    DBusuarios.write("[checkindate]: {}\n".format(checkindate))
    DBusuarios.write("[checkoutdate]: {}\n".format(checkoutdate))
    DBusuarios.write("[adults]: {}\n".format(adults))
    DBusuarios.write("[code]: {}\n".format(code))
    DBusuarios.write("[maxflightprice]: {}\n".format(maxflightprice))
    DBusuarios.write("[roomQuantity]: {}\n".format(roomQuantity))
    DBusuarios.write("[radius]: {}\n".format(radius))
    DBusuarios.write("[minPrice]: {}\n".format(minPrice))
    DBusuarios.write("[maxPrice]: {}\n".format(maxPrice))
    DBusuarios.write("\n")
    #escriure-les totes si van
    DBusuarios.close()

@app.route("/message", methods=['GET', 'POST'])
def message():
    """
    Entrypoint para todas las comunicaciones

    :return:
    """
    global busquedas
    

    # if request.form.has_key('message'):
    if 'message' in request.args:
        if request.args['message'] == 'search':
            checkindate = None
            checkoutdate = None
            adults = None
            code = None
            maxflightprice = None
            roomQuantity = None
            radius = None
            minPrice = None
            maxPrice = None
            if 'checkindate' in request.args: checkindate = request.args['checkindate']
            if 'checkoutdate' in request.args: checkoutdate = request.args['checkoutdate']
            if 'adults' in request.args: adults = request.args['adults']
            if 'code' in request.args: code = request.args['code']
            if 'maxflightprice' in request.args: maxflightprice = request.args['maxflightprice']
            if 'roomQuantity' in request.args: roomQuantity = request.args['roomQuantity']
            if 'radius' in request.args: radius = request.args['radius']
            if 'minPrice' in request.args: minPrice = request.args['minPrice']
            if 'maxPrice' in request.args: maxPrice = request.args['maxPrice']

            log.info('checkindate = ' + checkindate)
            log.info('checkoutdate = ' + checkoutdate)
            log.info('adults = ' + adults)
            log.info('code = ' + code)
            log.info('maxflightprice = ' + maxflightprice)
            log.info('roomQuantity = ' + roomQuantity)
            log.info('radius = ' + radius)
            log.info('minPrice = ' + minPrice)
            log.info('maxPrice = ' + maxPrice)

            guardarPreferencias(checkindate,checkoutdate,adults,code,maxflightprice,roomQuantity,radius,minPrice,maxPrice)

            return inicia_busqueda(
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
        
        elif request.args['message'] == 'pay':
            iban = None
            name = None
            if 'iban' in request.args: iban = request.args['iban']
            if 'name' in request.args: name = request.args['name']

            return pagar(name, iban)
        
        elif request.args['message'] == 'rating':
            rating = None
            if 'rating' in request.args: rating = request.args['rating']

            return valorar(rating)
    
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
        log.info('AQUI NO DEBERIA LLEGAR WTF')
        return 'OK'

def inicia_busqueda(checkindate, checkoutdate, adults, code, maxflightprice, roomQuantity, radius, minPrice, maxPrice):
    if checkindate is None: checkindate = ''
    if checkoutdate is None: checkoutdate = ''
    if adults is None: adults = ''
    log.info("checkindate = " + checkindate)
    log.info("checkoutdate = " + checkoutdate)
    log.info("adults = " + adults)
    log.info("code = " + str(code))

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

        busquedas[busquedaid] = ['PENDING', checkindate, checkoutdate, adults, code, maxflightprice, roomQuantity, radius, minPrice, maxPrice]
        log.info("presentadd: " + presentadd)

        mess = f'BUSQ|{busquedaid},{checkindate},{checkoutdate},{adults},{code},{maxflightprice},{roomQuantity},{radius},{minPrice},{maxPrice}'
        resp = requests.get(presentadd + '/message', params={'message': mess}).text
        if 'ERROR' not in resp:
            resultados = (ast.literal_eval(resp))
            busquedas[busquedaid][0] = 'DONE'
            log.info('Respuesta de Presentación recibida')
            return mostrarResultados(resultados)
        else:
            busquedas[busquedaid][0] = 'ERROR: FAILED PRESENTACION'
            log.info('Respuesta de Presentación recibida')
    # Solver no encontrado
    else:
        busquedas[busquedaid][0] = 'ERROR: FAILED SERVER' #['FAILED DS', checkindate, checkoutdate, adults, code, maxflightprice, roomQuantity, radius, minPrice, maxPrice]

def mostrarResultados(resultados):
    alojamientos = resultados['alojamientos']
    log.info('Se han recibido ' + str(len(alojamientos)) + ' alojamientos')
    # En el html, los datos de los alojamientos están ordenados como:
    # [NOMBRE, ID, RATING, DIRECCION, DESCRIPCION, ADULTOS, PRECIO]
    alojamientosArray = []
    id = 0
    for oferta in alojamientos:
        singleOferta = []
        singleOferta.append(id)
        singleOferta.append(oferta['name'])
        singleOferta.append(oferta['hotelId'])
        singleOferta.append(oferta['rating'])
        singleOferta.append(oferta['address'])
        singleOferta.append(oferta['description'])
        singleOferta.append(oferta['adults'])
        singleOferta.append(oferta['price'])
        alojamientosArray.append(singleOferta)
        id += 1


    transportes = resultados['transportes']
    log.info('Se han recibido ' + str(len(transportes)) + ' transportes:')
    log.info(str(transportes))

    transportesArray = []
    id = 0;
    for oferta in transportes:
        singleOferta = []
        singleOferta.append(id)
        singleOferta.append(oferta['salida'])
        singleOferta.append(oferta['llegada'])
        singleOferta.append(oferta['companyia'])
        singleOferta.append(oferta['number'])
        singleOferta.append(oferta['price'])
        transportesArray.append(singleOferta)
        id += 1

    log.info("Cargando todas las ofertas en el html...")
    log.info("Alojamientos: " + str(alojamientosArray))
    log.info("Desplazamientos: " + str(transportesArray))

    session['alojamientos'] = alojamientosArray
    session['transportes'] = transportesArray
    return redirect('/ofertas')

def pagar(name, iban):
    tesoreroadd = requests.get(diraddress + '/message', params={'message': f'SEARCH|TESOR'}).text

    if 'OK' in tesoreroadd:

        # Le quitamos el OK de la respuesta
        tesoreroadd = tesoreroadd[4:]

        mess = f'PAY|{name},{iban}'
        resp = requests.get(tesoreroadd + '/message', params={'message': mess}).text
        if 'ERROR' not in resp:
            param = resp.split(',')
            nombre, iban = param

            log.info('Ha pagado guay')

            alojamientoSeleccionado = session['alojamientos'][int(session['alojamientoSeleccionado'])]
            transporteSeleccionado = session['transportes'][int(session['transporteSeleccionado'])]

            session['name'] = name
            session['iban'] = iban

            log.info("TRANSPORTE = " + str(transporteSeleccionado))

            guardarItinerarioActivo(alojamientoSeleccionado, transporteSeleccionado, nombre, iban)

            return redirect('/historial')
            # return render_template('form_itinerario.html')
        else:
            log.info('No ha pagado guay')
    # Solver no encontrado
    # else:
        # busquedas[busquedaid][0] = 'ERROR: FAILED SERVER'

def valorar(rating):

    alojamientoSeleccionado = session['alojamientos'][int(session['alojamientoSeleccionado'])]
    transporteSeleccionado = session['transportes'][int(session['transporteSeleccionado'])]

    name = session['name']

    guardarValoracion(name, alojamientoSeleccionado, transporteSeleccionado, rating)
    guardarItinerarioRealizado(name, alojamientoSeleccionado, transporteSeleccionado)

    return redirect('/')

def guardarValoracion(name, alojamiento, transporte, rating):
    DBvaloraciones=open("DB/valoraciones.txt","a+")

    DBvaloraciones.write("[Name]: {}\n".format(name))
    DBvaloraciones.write("[Rating]: {}\n".format(rating))
    DBvaloraciones.write("[checkintime]: {}\n".format(transporte[1]))
    DBvaloraciones.write("[checkouttime]: {}\n".format(transporte[2]))
    DBvaloraciones.write("[adults]: {}\n".format(alojamiento[6]))
    DBvaloraciones.write("[carrierCode]: {}\n".format(transporte[3]))
    DBvaloraciones.write("[flightnumber]: {}\n".format(transporte[4]))
    DBvaloraciones.write("[flightprice]: {}\n".format(transporte[5]))
    DBvaloraciones.write("[hotelname]: {}\n".format(alojamiento[1]))
    DBvaloraciones.write("[hotelid]: {}\n".format(alojamiento[2]))
    DBvaloraciones.write("[hotelrating]: {}\n".format(alojamiento[3]))
    DBvaloraciones.write("[hoteladdress]: {}\n".format(alojamiento[4]))
    DBvaloraciones.write("[roomdescription]: {}\n".format(alojamiento[5]))
    DBvaloraciones.write("[roomprice]: {}\n".format(alojamiento[7]))
    DBvaloraciones.write("\n")
    #escriure-les totes si van
    DBvaloraciones.close()

def guardarItinerarioRealizado(name, alojamiento, transporte):
    DBitinerariosrealizados=open("DB/itinerariosrealizados.txt","a+")

    DBitinerariosrealizados.write("[Name]: {}\n".format(name))
    DBitinerariosrealizados.write("[checkintime]: {}\n".format(transporte[1]))
    DBitinerariosrealizados.write("[checkouttime]: {}\n".format(transporte[2]))
    DBitinerariosrealizados.write("[adults]: {}\n".format(alojamiento[6]))
    DBitinerariosrealizados.write("[carrierCode]: {}\n".format(transporte[3]))
    DBitinerariosrealizados.write("[flightnumber]: {}\n".format(transporte[4]))
    DBitinerariosrealizados.write("[flightprice]: {}\n".format(transporte[5]))
    DBitinerariosrealizados.write("[hotelname]: {}\n".format(alojamiento[1]))
    DBitinerariosrealizados.write("[hotelid]: {}\n".format(alojamiento[2]))
    DBitinerariosrealizados.write("[hotelrating]: {}\n".format(alojamiento[3]))
    DBitinerariosrealizados.write("[hoteladdress]: {}\n".format(alojamiento[4]))
    DBitinerariosrealizados.write("[roomdescription]: {}\n".format(alojamiento[5]))
    DBitinerariosrealizados.write("[roomprice]: {}\n".format(alojamiento[7]))
    DBitinerariosrealizados.write("\n")
    #escriure-les totes si van
    DBitinerariosrealizados.close()

def guardarItinerarioActivo(alojamiento, transporte, name, iban):
    DBitinerarios=open("DB/itinerarios.txt","a+")

    DBitinerarios.write("[Name]: {}\n".format(name))
    DBitinerarios.write("[IBAN]: {}\n".format(iban))
    DBitinerarios.write("[checkintime]: {}\n".format(transporte[1]))
    DBitinerarios.write("[checkouttime]: {}\n".format(transporte[2]))
    DBitinerarios.write("[adults]: {}\n".format(alojamiento[6]))
    DBitinerarios.write("[carrierCode]: {}\n".format(transporte[3]))
    DBitinerarios.write("[flightnumber]: {}\n".format(transporte[4]))
    DBitinerarios.write("[flightprice]: {}\n".format(transporte[5]))
    DBitinerarios.write("[hotelname]: {}\n".format(alojamiento[1]))
    DBitinerarios.write("[hotelid]: {}\n".format(alojamiento[2]))
    DBitinerarios.write("[hotelrating]: {}\n".format(alojamiento[3]))
    DBitinerarios.write("[hoteladdress]: {}\n".format(alojamiento[4]))
    DBitinerarios.write("[roomdescription]: {}\n".format(alojamiento[5]))
    DBitinerarios.write("[roomprice]: {}\n".format(alojamiento[7]))
    DBitinerarios.write("\n")
    #escriure-les totes si van
    DBitinerarios.close()


@app.route('/historial')
def mostrarHistorial():
    name = session['name']
    iban = session['iban']

    alojamientoSeleccionado = session['alojamientos'][int(session['alojamientoSeleccionado'])]
    transporteSeleccionado = session['transportes'][int(session['transporteSeleccionado'])]

    log.info('Renderizando ofertas')
    return render_template('historial.html', alojamiento = alojamientoSeleccionado, transporte = transporteSeleccionado, name = name, iban = iban)


@app.route('/ofertas')
def mostrarOfertas():
    alojamientos = session['alojamientos']
    transportes = session['transportes']

    log.info('Renderizando ofertas')
    return render_template('ofertas.html', alojamientos=alojamientos, transportes = transportes)
    

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    alojamientoSeleccionado = request.form['alojamientoSeleccionado']
    transporteSeleccionado = request.form['transporteSeleccionado']

    alojamientoSeleccionado = int(alojamientoSeleccionado.replace('/',''))
    transporteSeleccionado = int(transporteSeleccionado.replace('/',''))

    session['alojamientoSeleccionado'] = alojamientoSeleccionado
    session['transporteSeleccionado'] = transporteSeleccionado

    log.info("Ha seleccionado el alojamiento '{}'".format(alojamientoSeleccionado))
    log.info("Ha seleccionado el transporte '{}'".format(transporteSeleccionado))

    log.info(request.form)
    log.info(str(session['alojamientos']))
    alojamiento = session['alojamientos'][alojamientoSeleccionado]
    transporte = session['transportes'][transporteSeleccionado]
    preciototal = "{:.2f}".format(float(alojamiento[7]) + float(transporte[5]))

    return render_template('checkout.html', alojamiento=alojamiento, transporte=transporte, preciototal=preciototal)


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
    agenttype = 'USER'
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
        app.secret_key = 'super secret key'

        app.run(host=hostname, port=port, debug=False, use_reloader=False)

        mess = f'UNREGISTER|{clientid}'
        requests.get(diraddress + '/message', params={'message': mess})
    else:
        print('Unable to register')
