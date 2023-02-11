import os

import redis
import requests
from environs import Env
from flask import Flask, request

from format_message import get_total_price
from moltin_helpers import (add_product_to_cart, get_all_categories,
                            get_cart_items, get_category_by_slug,
                            get_image_by_id, get_moltin_access_token,
                            get_product_by_id, get_products_by_category_id)

app = Flask(__name__)
_database = None
env = Env()
env.read_env()
FACEBOOK_TOKEN = env("PAGE_ACCESS_TOKEN")
MOLTIN_CLIENT_ID = env('MOLTIN_CLIENT_ID')
MOLTIN_CLIENT_SECRET = env('MOLTIN_CLIENT_SECRET')


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == env("VERIFY_TOKEN"):
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"]["text"]
                    handle_users_reply(sender_id, message_text=message_text)
                elif messaging_event.get("postback"):
                    sender_id = messaging_event["sender"]["id"]
                    payload = messaging_event["postback"]["payload"]
                    handle_users_reply(sender_id, payload=payload)
    return "ok", 200


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.getenv('DATABASE_PASSWORD')
        database_host = os.getenv('DATABASE_HOST')
        database_port = os.getenv('DATABASE_PORT')
        _database = redis.Redis(host=database_host, port=int(database_port), password=database_password)
    return _database


def handle_users_reply(sender_id, message_text=None, payload=None):
    db = get_database_connection()
    if message_text == "/start":
        user_state = "START"
    else:
        user_state = db.get(f'facebook_id_{sender_id}').decode('utf-8')
    states_functions = {
        'START': handle_menu,
        'CART': handle_cart,
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text, payload)
    db.set(f'facebook_id_{sender_id}', next_state)


def handle_menu(recipient_id, message_text, payload):
    moltin_access_token = get_moltin_access_token(MOLTIN_CLIENT_ID, MOLTIN_CLIENT_SECRET)
    if payload:
        button_name, some_id = payload.split(';')
        if button_name == 'Категория':
            category_id = some_id
            pizzas = get_products_by_category_id(moltin_access_token, category_id)
        elif button_name == 'Добавить в корзину':
            product_id = some_id
            add_product_to_cart(moltin_access_token, product_id, recipient_id)
            pizza = get_product_by_id(moltin_access_token, product_id)
            message = f'В корзину добавлена пицца {pizza.get("name")}'
            send_message(recipient_id, message)
            return 'START'
        elif button_name == 'Корзина':
            handle_cart(recipient_id, message_text, payload)
            return 'CART'
        else:
            front_page_category = get_category_by_slug(moltin_access_token, 'main')[0]
            category_id = front_page_category.get('id')
            pizzas = get_products_by_category_id(moltin_access_token,
                                                 front_page_category.get('id'))
    else:
        front_page_category = get_category_by_slug(moltin_access_token, 'main')[0]
        category_id = front_page_category.get('id')
        pizzas = get_products_by_category_id(moltin_access_token,
                                             front_page_category.get('id'))

    menu_main_card = get_menu_main_card()
    menu_cards = [menu_main_card, ]

    for pizza in pizzas:
        product_card = get_product_card(pizza, moltin_access_token)
        menu_cards.append(product_card)

    categories = get_all_categories(moltin_access_token)
    categories_card = get_categories_card(categories, category_id)
    menu_cards.append(categories_card)

    headers = {
        'Content-Type': 'application/json',
    }
    json_data = {
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
        f'https://graph.facebook.com/v2.6/me/messages?access_token={FACEBOOK_TOKEN}',
        headers=headers,
        json=json_data,
    )
    response.raise_for_status()
    return 'START'


def handle_cart(recipient_id, message_text, payload):
    moltin_access_token = get_moltin_access_token(MOLTIN_CLIENT_ID, MOLTIN_CLIENT_SECRET)
    cart_items = get_cart_items(moltin_access_token, recipient_id)
    if payload:
        button_name, something = payload.split(';')
        if button_name == 'В меню':
            handle_menu(recipient_id, message_text, payload)
            return 'START'
    cart_cards = [get_cart_main_card(cart_items), ]
    headers = {
        'Content-Type': 'application/json',
    }
    json_data = {
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
        f'https://graph.facebook.com/v2.6/me/messages?access_token={FACEBOOK_TOKEN}',
        headers=headers,
        json=json_data,
    )
    response.raise_for_status()
    return 'CART'


def get_cart_main_card(cart_items):
    order_price = get_total_price(cart_items)
    menu_cart_card = {
        'title': 'Ваша корзина',
        'subtitle': f'Ваш заказ на сумму {order_price} р.',
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


def get_product_card(product, moltin_access_token):
    image = get_image_by_id(moltin_access_token,
                            product.get('relationships').get('main_image').get('data').get('id'))
    product_card = {
        'title': f'{product.get("name")} ({product.get("price")[0].get("amount")} р.) ',
        'subtitle': product.get('description'),
        'image_url': image.get('link').get('href'),
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


def send_message(recipient_id, message_text):
    params = {"access_token": FACEBOOK_TOKEN}
    headers = {"Content-Type": "application/json"}
    request_content = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    }
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, headers=headers, json=request_content
    )
    response.raise_for_status()


if __name__ == '__main__':
    app.run(debug=True)
