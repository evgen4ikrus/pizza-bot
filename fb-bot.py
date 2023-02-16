import json
import os

import redis
import requests
from environs import Env
from flask import Flask, request

from format_message import get_total_price
from moltin_helpers import (add_product_to_cart, delete_product_from_cart,
                            get_cart_items, get_moltin_access_token,
                            get_product_by_id)

app = Flask(__name__)
_database = None


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == os.getenv('VERIFY_TOKEN'):
            return 'Verification token mismatch', 403
        return request.args['hub.challenge'], 200

    return 'Hello world', 200


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data['object'] == 'page':
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                if messaging_event.get('message'):
                    sender_id = messaging_event['sender']['id']
                    message_text = messaging_event['message']['text']
                    handle_users_reply(sender_id, message_text=message_text)
                elif messaging_event.get('postback'):
                    sender_id = messaging_event['sender']['id']
                    payload = messaging_event['postback']['payload']
                    handle_users_reply(sender_id, payload=payload)
    return 'ok', 200


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.getenv('DATABASE_PASSWORD')
        database_host = os.getenv('DATABASE_HOST')
        database_port = os.getenv('DATABASE_PORT')
        _database = redis.Redis(host=database_host, port=int(database_port),
                                password=database_password, decode_responses=True)
    return _database


def handle_users_reply(sender_id, message_text=None, payload=None):
    env = Env()
    env.read_env()
    moltin_client_id = env('MOLTIN_CLIENT_ID')
    moltin_client_secret = env('MOLTIN_CLIENT_SECRET')
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    facebook_token = env('PAGE_ACCESS_TOKEN')
    db = get_database_connection()
    if message_text:
        user_state = 'START'
    else:
        user_state = db.get(f'facebook_id_{sender_id}')
    states_functions = {
        'START': handle_menu,
        'CART': handle_cart,
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text, payload, db, moltin_access_token, facebook_token)
    db.set(f'facebook_id_{sender_id}', next_state)


def handle_menu(recipient_id, message_text, payload, db, moltin_access_token, facebook_token):
    if payload:
        button_name, some_id = payload.split(';')
        if button_name == 'Категория':
            categories = json.loads(db.get('categories'))
            category_id = some_id
            current_category = None
            for category in categories:
                if category.get('id') == category_id:
                    current_category = category
                    break
            pizzas = current_category.get('products')
        elif button_name == 'Добавить в корзину':
            product_id = some_id
            add_product_to_cart(moltin_access_token, product_id, recipient_id)
            pizza = get_product_by_id(moltin_access_token, product_id)
            message = f'В корзину добавлена пицца - {pizza.get("name")}'
            send_message(recipient_id, message, facebook_token)
            return 'START'
        elif button_name == 'Корзина':
            handle_cart(recipient_id, message_text, payload, db, moltin_access_token, facebook_token)
            return 'CART'
        else:
            front_page_category = json.loads(db.get('menu'))
            category_id = front_page_category.get('id')
            pizzas = front_page_category.get('products')
    else:
        front_page_category = json.loads(db.get('menu'))
        category_id = front_page_category.get('id')
        pizzas = front_page_category.get('products')

    menu_main_card = get_menu_main_card()
    menu_cards = [menu_main_card, ]

    for pizza in pizzas:
        product_card = get_product_card(pizza)
        menu_cards.append(product_card)

    categories = json.loads(db.get('categories'))
    categories_card = get_categories_card(categories, category_id)
    menu_cards.append(categories_card)

    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
        'recipient': {
            'id': recipient_id,
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': menu_cards,
                },
            },
        },
    }
    response = requests.post(
        f'https://graph.facebook.com/v2.6/me/messages?access_token={facebook_token}',
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    return 'START'


def handle_cart(recipient_id, message_text, payload, db, moltin_access_token, facebook_token):
    if payload:
        button_name, some_id = payload.split(';')
        if button_name == 'В меню':
            handle_menu(recipient_id, message_text, payload, db, moltin_access_token, facebook_token)
            return 'START'
        elif button_name == 'Убрать из корзины':
            product_id = some_id
            delete_product_from_cart(moltin_access_token, recipient_id, product_id)
            message = f'Пицца удалена из корзины'
            send_message(recipient_id, message, facebook_token)
        elif button_name == 'Добавить ещё одну':
            product_id = some_id
            add_product_to_cart(moltin_access_token, product_id, recipient_id)
            pizza_name = get_product_by_id(moltin_access_token, product_id).get('name')
            message = f'В корзину добавлен еще одна пицца - {pizza_name}'
            send_message(recipient_id, message, facebook_token)
    cart_pizzas = get_cart_items(moltin_access_token, recipient_id)
    cart_cards = [get_cart_main_card(cart_pizzas), ]
    if cart_pizzas:
        for pizza in cart_pizzas:
            product_card = get_product_cart_card(pizza)
            cart_cards.append(product_card)

    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
        'recipient': {
            'id': recipient_id,
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': cart_cards,
                },
            },
        },
    }
    response = requests.post(
        f'https://graph.facebook.com/v2.6/me/messages?access_token={facebook_token}',
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    return 'CART'


def get_product_cart_card(product):
    product_card = {
        'title': f'{product.get("name")} {product.get("quantity")} шт. за {product.get("value").get("amount")} р.',
        'subtitle': product.get('description'),
        'image_url': product.get('image').get('href'),
        'buttons': [
            {
                'type': 'postback',
                'title': 'Добавить ещё одну',
                'payload': f'Добавить ещё одну;{product.get("product_id")}',
            },
            {
                'type': 'postback',
                'title': 'Убрать из корзины',
                'payload': f'Убрать из корзины;{product.get("id")}',
            },
        ],
    }
    return product_card


def get_cart_main_card(cart_pizzas):
    if cart_pizzas:
        order_price = get_total_price(cart_pizzas)
        subtitle = f'Ваш заказ на сумму {order_price} р.'
    else:
        subtitle = 'Ваша корзина пуста'
    menu_cart_card = {
        'title': 'Корзина',
        'subtitle': subtitle,
        'image_url': 'https://img.freepik.com/premium-vector/shopping-trolley-full-of-food-fruit-products-grocery-goods-grocery-shopping-cart_625536-441.jpg',
        'buttons': [
            {
                'type': 'postback',
                'title': 'Самовывоз',
                'payload': 'Самовывоз;',
            },
            {
                'type': 'postback',
                'title': 'Доставка',
                'payload': 'Доставка;',
            },
            {
                'type': 'postback',
                'title': 'В меню',
                'payload': 'В меню;',
            },
        ],
    }
    return menu_cart_card


def get_menu_main_card():
    menu_main_card = {
        'title': 'Меню',
        'subtitle': 'Здесь вы можете выбрать один из вариантов',
        'image_url': 'https://cdn1.vectorstock.com/i/1000x1000/21/30/big-pizza-logo-vector-31052130.jpg',
        'buttons': [
            {
                'type': 'postback',
                'title': 'Корзина',
                'payload': 'Корзина;',
            },
            {
                'type': 'postback',
                'title': 'Акции',
                'payload': 'Акции;',
            },
            {
                'type': 'postback',
                'title': 'Сделать заказ',
                'payload': 'Сделать заказ;',
            },
        ],
    }
    return menu_main_card


def get_product_card(product):
    product_card = {
        'title': f'{product.get("name")} ({product.get("price")[0].get("amount")} р.)',
        'subtitle': product.get('description'),
        'image_url': product.get('image_link'),
        'buttons': [
            {
                'type': 'postback',
                'title': 'Добавить в корзину',
                'payload': f'Добавить в корзину;{product.get("id")}',
            },
        ],
    }
    return product_card


def get_categories_card(categories, category_id):
    category_buttons = []
    for category in categories:
        if category.get('id') == category_id:
            continue
        category_button = {
            'type': 'postback',
            'title': category.get('name'),
            'payload': f'Категория;{category.get("id")}',
        }
        category_buttons.append(category_button)
    categories_card = {
        'title': 'Не нашли нужную пиццу?',
        'subtitle': 'Остальные пиццы можно посмотреть в одной из категорий',
        'image_url': 'https://primepizza.ru/uploads/position/large_0c07c6fd5c4dcadddaf4a2f1a2c218760b20c396.jpg',
        'buttons': category_buttons
    }
    return categories_card


def send_message(recipient_id, message_text, facebook_token):
    params = {'access_token': facebook_token}
    headers = {'Content-Type': 'application/json'}
    request_content = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': message_text
        }
    }
    response = requests.post(
        'https://graph.facebook.com/v2.6/me/messages',
        params=params, headers=headers, json=request_content
    )
    response.raise_for_status()


if __name__ == '__main__':
    app.run(debug=True)
