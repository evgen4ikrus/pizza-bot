import os
import re

from environs import Env
from transliterate import translit

from file_helpers import get_json
from moltin_helpers import (create_main_image_relationship, download_image,
                            download_product, get_moltin_access_token)


def main():
    env = Env()
    env.read_env()
    products_path = env('PRODUCTS_FILE', 'products.json')
    moltin_client_id = env('MOLTIN_CLIENT_ID')
    moltin_client_secret = env('MOLTIN_CLIENT_SECRET')
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)

    raw_products = get_json(os.path.join(products_path))
    for raw_product in raw_products:
        product_name = raw_product['name']
        en_product_name = translit(product_name, language_code='ru', reversed=True).replace(' ', '_')
        slug = re.sub('[^a-z]', '', en_product_name)
        product = download_product(moltin_access_token, product_name, raw_product['description'],
                                   raw_product['price'], slug)
        image = download_image(moltin_access_token, raw_product['product_image']['url'])
        create_main_image_relationship(moltin_access_token, product['id'], image['id'])


if __name__ == '__main__':
    main()
