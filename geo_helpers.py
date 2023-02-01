import requests
from geopy import distance

from moltin_helpers import get_all_pizzerias, get_moltin_access_token


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lat, lon


def get_nearest_pizzeria(coordinates, moltin_client_id, moltin_client_secret, flow_slug):
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    pizzerias = get_all_pizzerias(moltin_access_token, flow_slug)
    nearest_pizzeria = min(pizzerias, key=lambda pizzeria: distance.distance((pizzeria['latitude'], pizzeria['longitude']), coordinates).km)
    return nearest_pizzeria
