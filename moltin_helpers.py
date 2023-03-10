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


def download_product(moltin_access_token, name, description, price, slug):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'type': 'product',
            'name': name,
            'slug': slug,
            'sku': name,
            'description': description,
            'manage_stock': False,
            'price': [
                {
                    'amount': price,
                    'currency': 'USD',
                    'includes_tax': False,
                },
            ],
            'status': 'live',
            'commodity_type': 'physical',
        },
    }
    response = requests.post('https://api.moltin.com/v2/products', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['data']


def download_image(moltin_access_token, image_url):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    files = {
        'file_location': (None, image_url),
    }
    response = requests.post('https://api.moltin.com/v2/files', headers=headers, files=files)
    response.raise_for_status()
    return response.json()['data']


def get_image_by_id(moltin_access_token, image_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/files/{image_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_all_images(moltin_access_token):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get('https://api.moltin.com/v2/files', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def delete_image(moltin_access_token, image_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }

    response = requests.delete(f'https://api.moltin.com/v2/files/{image_id}', headers=headers)
    response.raise_for_status()


def get_all_products(moltin_access_token):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get('https://api.moltin.com/v2/products', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def delete_product(moltin_access_token, product_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.delete(f'https://api.moltin.com/v2/products/{product_id}', headers=headers)
    response.raise_for_status()


def create_main_image_relationship(moltin_access_token, product_id, image_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'type': 'main_image',
            'id': image_id,
        },
    }
    response = requests.post(
        f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image',
        headers=headers,
        json=payload,
    )
    response.raise_for_status()


def create_flow(moltin_access_token, flow_name, slug, description):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'type': 'flow',
            'name': flow_name,
            'slug': slug,
            'description': description,
            'enabled': True,
        },
    }
    response = requests.post('https://api.moltin.com/v2/flows', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['data']


def get_flow(moltin_access_token, flow_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/flows/{flow_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def create_flow_field(moltin_access_token, flow_id, name, slug, field_type, description):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'type': 'field',
            'name': name,
            'slug': slug,
            'field_type': field_type,
            'description': description,
            'required': True,
            'enabled': True,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow_id,
                    },
                },
            },
        },
    }
    response = requests.post('https://api.moltin.com/v2/fields', headers=headers, json=payload)
    response.raise_for_status()


def get_all_flow_fields(moltin_access_token, flow_slug):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/flows/{flow_slug}/fields', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def create_pizzeria(moltin_access_token: str, flow_slug: str,
                    alias_field_slug: str, alias: str,
                    address_field_slug: str, address: str,
                    longitude_field_slug: str, longitude: float,
                    latitude_field_slug: str, latitude: float,
                    courier_id_slug: str, courier_id: str):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'type': 'entry',
            alias_field_slug: alias,
            address_field_slug: address,
            longitude_field_slug: longitude,
            latitude_field_slug: latitude,
            courier_id_slug: courier_id,
        },
    }
    response = requests.post(f'https://api.moltin.com/v2/flows/{flow_slug}/entries', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def create_customer_address(moltin_access_token: str, flow_slug: str,
                            longitude_field_slug: str, longitude: float,
                            latitude_field_slug: str, latitude: float):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'type': 'entry',
            longitude_field_slug: longitude,
            latitude_field_slug: latitude,
        },
    }
    response = requests.post(f'https://api.moltin.com/v2/flows/{flow_slug}/entries', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def delete_entry(moltin_access_token, flow_slug, entry_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }

    response = requests.delete(f'https://api.moltin.com/v2/flows/{flow_slug}/entries/{entry_id}', headers=headers)
    response.raise_for_status()


def get_all_entries(moltin_access_token, flow_slug):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/flows/{flow_slug}/entries', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def create_user_cart(moltin_access_token, cart_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def add_product_to_cart(moltin_access_token, product_id, cart_id, quantity=1):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': int(quantity),
        }
    }
    response = requests.post(url=f'https://api.moltin.com/v2/carts/{cart_id}/items', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_cart_items(moltin_access_token, cart_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    url = f'https://api.moltin.com/v2/carts/{cart_id}/items'
    response = requests.get(url=url, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_product_by_id(moltin_access_token, product_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/products/{product_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def delete_product_from_cart(moltin_access_token, cart_id, product_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.delete(f'https://api.moltin.com/v2/carts/{cart_id}/items/{product_id}', headers=headers)
    response.raise_for_status()


def create_customer(moltin_access_token, name, email):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'name': name,
            'email': email,
            'type': 'customer',
        }
    }
    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_entry(moltin_access_token, flow_slug, entry_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/flows/{flow_slug}/entries/{entry_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def create_category(moltin_access_token, name, slug, status='live'):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }

    payload = {
        'data': {
            'type': 'category',
            'name': name,
            'slug': slug,
            'status': status,
        },
    }

    response = requests.post('https://api.moltin.com/v2/categories', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['data']


def add_category_product(moltin_access_token, category_id, product_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': [
            {
                'type': 'category',
                'id': category_id,
            },
        ],
    }
    response = requests.post(
        f'https://api.moltin.com/v2/products/{product_id}/relationships/categories',
        headers=headers,
        json=payload,
    )
    response.raise_for_status()


def get_category_by_id(moltin_access_token, category_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/categories/{category_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_products_by_category_id(moltin_access_token, category_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    params = {
        'filter': f'eq(category.id,{category_id})'
    }
    response = requests.get('https://api.moltin.com/v2/products', params=params, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_all_categories(moltin_access_token):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.get('https://api.moltin.com/v2/categories', headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_category_by_slug(moltin_access_token, category_slug):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    params = {
        'filter': f'eq(slug,{category_slug})'
    }
    response = requests.get('https://api.moltin.com/v2/categories', params=params, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def delete_category(moltin_access_token, category_id):
    headers = {
        'Authorization': f'Bearer {moltin_access_token}',
    }
    response = requests.delete(f'https://api.moltin.com/v2/categories/{category_id}', headers=headers)
    response.raise_for_status()
