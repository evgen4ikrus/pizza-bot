import json

from environs import Env
from transliterate import translit

from moltin_helpers import (create_main_image_relationship, download_image,
                            download_product, get_moltin_access_token)


def get_json(file):
    with open(file, 'r', encoding='UTF-8') as file:
        file_contents = file.read()
    contents = json.loads(file_contents)
    return contents


def main():
    env = Env()
    env.read_env()
    moltin_client_id = env('MOLTIN_CLIENT_ID')
    moltin_client_secret = env('MOLTIN_CLIENT_SECRET')
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)

    pizzas = get_json('menu.json')
    for pizza in pizzas:
        pizza_name = pizza['name']
        en_pizza_name = translit(pizza_name, language_code='ru', reversed=True).replace(' ', '_')
        product = download_product(moltin_access_token, pizza['name'], pizza['description'], pizza['price'], en_pizza_name)
        image = download_image(moltin_access_token, pizza['product_image']['url'])
        create_main_image_relationship(moltin_access_token, product['id'], image['id'])


if __name__ == '__main__':
    main()
