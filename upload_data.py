import os
import re

from environs import Env
from transliterate import translit

from file_helpers import get_json
from moltin_helpers import (create_flow, create_flow_field,
                            create_main_image_relationship, create_pizzeria,
                            download_image, download_product,
                            get_moltin_access_token)


def upload_products(moltin_access_token, raw_products):
    for raw_product in raw_products:
        product_name = raw_product['name']
        en_product_name = translit(product_name, language_code='ru', reversed=True).replace(' ', '_')
        slug = re.sub('[^a-z]', '', en_product_name)
        product = download_product(moltin_access_token, product_name, raw_product['description'],
                                   raw_product['price'], slug)
        image = download_image(moltin_access_token, raw_product['product_image']['url'])
        create_main_image_relationship(moltin_access_token, product['id'], image['id'])


def create_pizzeria_flow(moltin_access_token):
    flow = create_flow(moltin_access_token, 'Pizzeria', 'pizzeria', 'Пиццерия')
    create_flow_field(moltin_access_token, flow['id'], 'Address', 'address', 'string', 'Адреса')
    create_flow_field(moltin_access_token, flow['id'], 'Alias', 'alias', 'string', 'Псевдоним')
    create_flow_field(moltin_access_token, flow['id'], 'Longitude', 'longitude', 'float', 'Долгота')
    create_flow_field(moltin_access_token, flow['id'], 'Latitude', 'latitude', 'float', 'Широта')
    create_flow_field(moltin_access_token, flow['id'], 'Courier id', 'courier_id', 'string', 'ID доставщика')


def upload_pizzerias(moltin_access_token, pizzerias):
    for pizzeria in pizzerias:
        create_pizzeria(moltin_access_token, 'pizzeria',
                        'alias', pizzeria['alias'],
                        'address', pizzeria['address']['full'],
                        'longitude', float(pizzeria['coordinates']['lon']),
                        'latitude', float(pizzeria['coordinates']['lat']),
                        'courier_id', pizzeria['courier_id'])


def create_customer_address_flow(moltin_access_token):
    customer_address_flow = create_flow(moltin_access_token, 'Customer Address', 'customer_address', 'Адрес заказчика')
    create_flow_field(moltin_access_token, customer_address_flow['id'], 'Latitude', 'latitude', 'float', 'Широта')
    create_flow_field(moltin_access_token, customer_address_flow['id'], 'Longitude', 'longitude', 'float', 'Долгота')


def main():
    env = Env()
    env.read_env()
    products_path = env('PRODUCTS_PATH', 'products.json')
    pizzerias_path = env('PIZZERIAS_PATH', 'pizzerias.json')
    moltin_client_id = env('MOLTIN_CLIENT_ID')
    moltin_client_secret = env('MOLTIN_CLIENT_SECRET')
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)

    products = get_json(os.path.join(products_path))
    pizzerias = get_json(os.path.join(pizzerias_path))

    upload_products(moltin_access_token, products)
    create_pizzeria_flow(moltin_access_token)
    upload_pizzerias(moltin_access_token, pizzerias)
    create_customer_address_flow(moltin_access_token)


if __name__ == '__main__':
    main()
