import json

from environs import Env

from moltin_helpers import (get_all_categories, get_category_by_slug,
                            get_image_by_id, get_moltin_access_token,
                            get_products_by_category_id)
from redis_tools import get_database_connection

_database = None


def get_menu(front_page_category_slug='main'):
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    front_page_category = get_category_by_slug(moltin_access_token, front_page_category_slug)[0]
    front_page_products = get_products_by_category_id(moltin_access_token,
                                                      front_page_category.get('id'))
    for product in front_page_products:
        image = get_image_by_id(moltin_access_token,
                                product.get('relationships').get('main_image').get('data').get('id'))
        product['image_link'] = image.get('link').get('href')
    front_page_category['products'] = front_page_products
    return front_page_category


def get_categories_with_products():
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    categories = get_all_categories(moltin_access_token)
    for category in categories:
        products = get_products_by_category_id(moltin_access_token, category.get('id'))
        for product in products:
            image = get_image_by_id(moltin_access_token,
                                    product.get('relationships').get('main_image').get('data').get('id'))
            product['image_link'] = image.get('link').get('href')
        category['products'] = products
    return categories


if __name__ == '__main__':
    env = Env()
    env.read_env()
    moltin_client_id = env('MOLTIN_CLIENT_ID')
    moltin_client_secret = env('MOLTIN_CLIENT_SECRET')
    db = get_database_connection()

    menu = get_menu()
    cached_menu = db.get('menu')
    if cached_menu:
        cached_menu = json.loads(cached_menu)
    if cached_menu != menu:
        db.set('menu', json.dumps(menu))

    categories_with_products = get_categories_with_products()
    cached_categories = db.get('categories')
    if cached_categories:
        cached_categories = json.loads(cached_categories)
    if cached_categories != categories_with_products:
        db.set('categories', json.dumps(categories_with_products))
