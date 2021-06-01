from amadeus import Client, ResponseError
import argparse



parser = argparse.ArgumentParser()
parser.add_argument('--checkin', type=str, help="Format YYYY-MM-DD")
parser.add_argument('--checkout', type=str, help="Format YYYY-MM-DD")
parser.add_argument('--adults', type=int, help="Number of adult guests (1-9) per room")




def printHotels(data):
    for hotel in data:
        hotelInfo = hotel['hotel']
        hotelName = hotelInfo['name']
        hotelDescription = hotelInfo['description']['text']
        # hotelPrice = hotelInfo['price']

        print("NOMBRE: ", hotelName)
        print("DESCRIPCION: ", hotelDescription)
        # print("PRICE: ", hotelPrice)
        print("===========================")
        # print(data[0])



amadeus = Client(
    client_id='Gu3svGYecxv4aPs2fusVIEloak3YSVxU',
    client_secret='aektZUqvk4SbaZns'
    )

# resp = hotels.search_circle(
#     check_in='2021-06-07',
#     check_out='2021-06-11',
#     latitude=41.3881972,
#     longitude=2.2039021,
#     currency='EUR',
#     max_rate=100,
#     radius=300
#     )

args = parser.parse_args()

if args.checkin is None:
    checkInDate = "2021-07-06"
else:
    checkInDate = args.checkin

if args.checkout is None:
    checkOutDate = "2021-07-11"
else:
    checkOutDate = args.checkout

if args.adults is None:
    adults = 2
else:
    adults = args.adults

try:
    response = amadeus.shopping.hotel_offers.get(
        cityCode = 'BCN',
        checkInDate = checkInDate,
        checkOutDate = checkOutDate,
        adults = adults,
        latitude = 36.7319625,
        longitude = -6.4393172,
        radius = 50,
        bestRateOnly = False
        )
    printHotels(response.data)
except ResponseError as error:
    print(error)


Información necesaria para vuelos: /shopping/flight-offers
    - originLocationCode "ABC"
    - destinationLocationCode "BCN"
    - departureDate "YYYY-MM-DD"
    - adults (int)
    * maxPrice (int)
    * returnDate

Información necesaria para hoteles: /shopping/hotel-offers
    - cityCode "BCN"
    - radius 50
    - radiusUnit "KM"
    - checkInDate "YYYY-MM-DD"
    - checkOutDate "YYYY-MM-DD"
    - adults (int)
    * roomQuantity (int)
    * ratings [1, 2, 3, 4]
    * bestRateOnly True (devolver sólo la oferta más barata para cada hotel)
    * priceRange "100-300"
    *^ currency "EUR"

