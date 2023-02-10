import os

import redis
import requests
from environs import Env
from flask import Flask, request

from moltin_helpers import (get_all_categories, get_category_by_slug,
                            get_image_by_id, get_moltin_access_token,
                            get_products_by_category_id)

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
                    recipient_id = messaging_event["recipient"]["id"]
                    message_text = messaging_event["message"]["text"]
                    handle_users_reply(sender_id, message_text)
    return "ok", 200


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.getenv('DATABASE_PASSWORD')
        database_host = os.getenv('DATABASE_HOST')
        database_port = os.getenv('DATABASE_PORT')
        _database = redis.Redis(host=database_host, port=int(database_port), password=database_password)
    return _database


def handle_users_reply(sender_id, message_text):
    db = get_database_connection()
    states_functions = {
        'START': send_menu,
    }
    recorded_state = db.get(f'facebook_id_{sender_id}')
    if not recorded_state or recorded_state.decode("utf-8") not in states_functions.keys():
        user_state = "START"
    else:
        user_state = recorded_state.decode("utf-8")
    if message_text == "/start":
        user_state = "START"
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    db.set(f'facebook_id_{sender_id}', next_state)


def get_menu_main_element():
    menu_main_element = {
        'title': 'Меню',
        'subtitle': 'Здесь вы можете выбрать один из вариантов',
        'image_url': 'https://cdn1.vectorstock.com/i/1000x1000/21/30/big-pizza-logo-vector-31052130.jpg',
        'buttons': [
            {
                'type': 'postback',
                'title': 'Корзина',
                'payload': 'Корзина',
            },
            {
                'type': 'postback',
                'title': 'Акции',
                'payload': 'Акции',
            },
            {
                'type': 'postback',
                'title': 'Сделать заказ',
                'payload': 'Сделать заказ',
            },
        ],
    }
    return menu_main_element


def get_product_element(product, moltin_access_token):
    image = get_image_by_id(moltin_access_token,
                            product.get('relationships').get('main_image').get('data').get('id'))
    product_element = {
        'title': f'{product.get("name")} ({product.get("price")[0].get("amount")} р.) ',
        'subtitle': product.get('description'),
        'image_url': image.get('link').get('href'),
        'buttons': [
            {
                'type': 'postback',
                'title': 'Добавить в корзину',
                'payload': product.get('id'),
            },
        ],
    }
    return product_element


def get_categories_element(categories):
    category_buttons = []
    for category in categories:
        if category.get('slug') == 'main':
            continue
        category_button = {
            'type': 'postback',
            'title': category.get('name'),
            'payload': category.get('id'),
        }
        category_buttons.append(category_button)
    categories_element = {
        'title': 'Не нашли нужную пиццу?',
        'subtitle': 'Остальные пиццы можно посмотреть в одной из категорий',
        'image_url': 'https://primepizza.ru/uploads/position/large_0c07c6fd5c4dcadddaf4a2f1a2c218760b20c396.jpg',
        'buttons': category_buttons
    }
    return categories_element


def send_menu(recipient_id, message_text):
    moltin_access_token = get_moltin_access_token(MOLTIN_CLIENT_ID, MOLTIN_CLIENT_SECRET)
    menu_main_element = get_menu_main_element()
    menu_elements = [menu_main_element, ]

    front_page_category = get_category_by_slug(moltin_access_token, 'main')
    front_page_pizzas = get_products_by_category_id(moltin_access_token,
                                                    front_page_category[0].get('id'))
    for pizza in front_page_pizzas:
        product_element = get_product_element(pizza, moltin_access_token)
        menu_elements.append(product_element)

    categories = get_all_categories(moltin_access_token)
    categories_element = get_categories_element(categories)
    menu_elements.append(categories_element)

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
                    'elements': menu_elements,
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

    if __name__ == '__main__':
        app.run(debug=True)
