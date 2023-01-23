from datetime import datetime

import requests

MOLTIN_ACCESS_TOKEN, TOKEN_CREATED_AT = None, None


def get_moltin_access_token(client_id, client_secret):
    global MOLTIN_ACCESS_TOKEN, TOKEN_CREATED_AT
    if MOLTIN_ACCESS_TOKEN:
        left_time = TOKEN_CREATED_AT - datetime.now().timestamp()
        minimum_seconds = 30
        if left_time > minimum_seconds:
            return MOLTIN_ACCESS_TOKEN
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }
    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()
    raw_response = response.json()
    MOLTIN_ACCESS_TOKEN = raw_response['access_token']
    TOKEN_CREATED_AT = raw_response['expires']
    return MOLTIN_ACCESS_TOKEN


def download_product(moltin_access_token, name, slug, description, price, sku):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'type': 'product',
            'name': name,
            'slug': slug,
            'sku': sku,
            'description': description,
            'manage_stock': False,
            'price': [
                {
                    'amount': price,
                    'currency': 'RUB',
                    'includes_tax': False,
                },
            ],
            'status': 'live',
            'commodity_type': 'physical',
        },
    }
    response = requests.post('https://api.moltin.com/v2/products', headers=headers, json=payload)
    response.raise_for_status()


def download_image(moltin_access_token):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    files = {
        'file_location': (None, 'https://dodopizza-a.akamaihd.net/static/Img/Products/Pizza/ru-RU/714c5eb8-be9a-4101-b46f-6ec9055c9416.jpg'),
    }
    response = requests.post('https://api.moltin.com/v2/files', headers=headers, files=files)
    response.raise_for_status()


def get_all_products(moltin_access_token):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get('https://api.moltin.com/v2/products', headers=headers)
    response.raise_for_status()
