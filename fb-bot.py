import requests
from environs import Env
from flask import Flask, request

from moltin_helpers import (get_all_products, get_image_by_id,
                            get_moltin_access_token)

app = Flask(__name__)
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
                    # message_text = messaging_event["message"]["text"]
                    send_message(sender_id, 'проверка связи')
                    send_menu(sender_id)

    return "ok", 200


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


def send_menu(recipient_id):
    moltin_access_token = get_moltin_access_token(MOLTIN_CLIENT_ID, MOLTIN_CLIENT_SECRET)
    products = get_all_products(moltin_access_token)[1:6]
    menu_products = [
        {
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
    ]
    for product in products:
        image = get_image_by_id(moltin_access_token,
                                product.get('relationships').get('main_image').get('data').get('id'))

        menu_product = {
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
        menu_products.append(menu_product)
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
                    'elements': menu_products,
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

    if __name__ == '__main__':
        app.run(debug=True)
