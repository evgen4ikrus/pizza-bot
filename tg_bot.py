import logging
import os

import redis
import telegram
from environs import Env
from geopy import distance
from requests.exceptions import HTTPError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, PreCheckoutQueryHandler, Updater)

from format_message import (create_cart_description,
                            create_product_description, get_total_price)
from geo_helpers import fetch_coordinates, get_nearest_place
from log_helpers import TelegramLogsHandler
from moltin_helpers import (add_product_to_cart, create_customer,
                            create_customer_address, delete_product_from_cart,
                            get_all_products, get_cart_items, get_entry,
                            get_image_by_id, get_moltin_access_token,
                            get_product_by_id)

_database = None
logger = logging.getLogger('tg_bot')


def get_menu_keyboard():
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    products = get_all_products(moltin_access_token)
    keyboard = [
        [InlineKeyboardButton(product.get('name'), callback_data=product.get('id'))]
        for product in products
    ]
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='Корзина')])
    return keyboard


def get_cart_keyboard(cart_items):
    keyboard = [
        [InlineKeyboardButton(f"Убрать из корзины {item.get('name')}", callback_data=item.get('id'))]
        for item in cart_items
    ]
    keyboard.insert(0, [InlineKeyboardButton('Оплатить', callback_data='Оплатить')])
    keyboard.append([InlineKeyboardButton('В меню', callback_data='Меню')])
    return keyboard


def start(bot, update):
    keyboard = get_menu_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text='Главное меню:', reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handle_menu(bot, update):
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    query = update.callback_query
    if query.data == 'Корзина':
        cart_items = get_cart_items(moltin_access_token, query.message.chat_id)
        message = create_cart_description(cart_items)
        keyboard = get_cart_keyboard(cart_items)
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
        return 'HANDLE_CART'
    product_id = '{}'.format(query.data)
    product = get_product_by_id(moltin_access_token, product_id)
    message = create_product_description(product)
    keyboard = [
        [InlineKeyboardButton('Добавить в корзину', callback_data=product_id)],
        [InlineKeyboardButton('Корзина', callback_data='Корзина')],
        [InlineKeyboardButton('Назад', callback_data='Назад')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if product.get('relationships'):
        image = get_image_by_id(moltin_access_token,
                                product.get('relationships').get('main_image').get('data').get('id'))
        image_link = image.get('link').get('href')
        bot.send_photo(chat_id=query.message.chat_id, caption=message, photo=image_link, reply_markup=reply_markup)
        bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        return 'HANDLE_DESCRIPTION'
    bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
    return 'HANDLE_DESCRIPTION'


def handle_description(bot, update):
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    query = update.callback_query
    if query.data == 'Назад':
        keyboard = get_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = 'Главное меню:'
        bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
        bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        return 'HANDLE_MENU'
    if query.data == 'Корзина':
        cart_items = get_cart_items(moltin_access_token, query.message.chat_id)
        message = create_cart_description(cart_items)
        keyboard = get_cart_keyboard(cart_items)
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
        return 'HANDLE_CART'
    product_id = query.data
    add_product_to_cart(moltin_access_token, product_id, query.message.chat_id)
    update.callback_query.answer("Товар добавлен в корзину")
    return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update):
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    query = update.callback_query
    if query.data == 'Меню':
        keyboard = get_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = 'Главное меню:'
        bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
        return 'HANDLE_MENU'
    if query.data == 'Оплатить':
        message = 'Пожалуйста введите Вашу электронную почту:'
        bot.send_message(text=message, chat_id=query.message.chat_id)
        return 'HANDLE_WAITING_EMAIL'
    delete_product_from_cart(moltin_access_token, query.message.chat_id, query.data)
    cart_items = get_cart_items(moltin_access_token, query.message.chat_id)
    message = create_cart_description(cart_items)
    keyboard = get_cart_keyboard(cart_items)
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.answer("Товар удален из корзину")
    bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
    return 'HANDLE_CART'


def handle_waiting_email(bot, update):
    user = update.effective_user
    name = f"{user.first_name} id:{user.id}"
    email = update.message.text
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    try:
        create_customer(moltin_access_token, name, email)
    except HTTPError:
        message = 'Произошла ошибка, возможно вы прислали несуществующий email. Попробуйте повторить попытку:'
        bot.send_message(text=message, chat_id=update.message.chat_id)
        return 'HANDLE_WAITING_EMAIL'
    message = f'Вы прислали нам эту эл. почту: {email}.\n\nТеперь пришлите нам Ваш адрес текстом или геолокацию:'
    bot.send_message(text=message, chat_id=update.message.chat_id)
    return 'HANDLE_WAITING_ADDRESS'


def handle_waiting_address(bot, update):
    address = update.message.text
    if address:
        customer_coordinates = fetch_coordinates(yandex_api_key, address)
        if not customer_coordinates:
            bot.send_message(text='Некорректный адрес, повторите попытку:', chat_id=update.message.chat_id)
            return 'HANDLE_WAITING_ADDRESS'
    else:
        if update.edited_message:
            message = update.edited_messageadd
        else:
            message = update.message
        customer_coordinates = (message.location.latitude, message.location.longitude)
    nearest_pizzeria = get_nearest_place(customer_coordinates, moltin_client_id, moltin_client_secret, 'pizzeria')
    raw_pizzeria_distance = distance.distance((nearest_pizzeria.get('latitude'), nearest_pizzeria.get('longitude')),
                                              customer_coordinates)
    pizzeria_distance = round(float((str(raw_pizzeria_distance)).split()[0]), 1)
    nearest_pizzeria_address = nearest_pizzeria["address"]
    pizzeria_id = nearest_pizzeria['id']
    courier_chat_id = nearest_pizzeria['courier_id']
    if pizzeria_distance <= 0.5:
        delivery_price = 'бесплатно'
    elif pizzeria_distance <= 5:
        delivery_price = 'за 100 рублей'
    elif pizzeria_distance <= 20:
        delivery_price = 'за 300 рублей'
    else:
        message = f'К сожалению, мы не можем доставить на этот адрес, он очень далеко от нас.\n' \
                  f'Но Вы можете, забрать пиццу из нашей пиццерии. ' \
                  f'Она находится в {pizzeria_distance} км. от вас! Вот её адрес: {nearest_pizzeria_address}.\n' \
                  f'Или введите другой адрес доставки:'
        bot.send_message(text=message, chat_id=update.message.chat_id)
        return 'HANDLE_WAITING_ADDRESS'
    customer_latitude, customer_longitude = customer_coordinates[0], customer_coordinates[1]
    customer_chat_id = update.message.chat_id
    keyboard = [
        [InlineKeyboardButton(
            'Доставка',
            callback_data=f'Доставка;{courier_chat_id},{customer_chat_id},{customer_latitude},{customer_longitude}'
        )],
        [InlineKeyboardButton('Самовывоз', callback_data=f'Самовывоз;{pizzeria_id}')]
    ]
    message = f'Может, заберете пиццу из нашей пиццерии неподалеку? ' \
              f'Она всего в {pizzeria_distance} км. от вас! ' \
              f'Вот её адрес: {nearest_pizzeria_address}.\n' \
              f'А можем и доставить {delivery_price}, нам не сложно:'
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(text=message, chat_id=update.message.chat_id, reply_markup=reply_markup)
    return 'HANDLE_WAITING_DELIVERY'


def handle_waiting_delivery(bot, update):
    query = update.callback_query
    command, about_delivery = query.data.split(';')
    if command == 'В меню':
        keyboard = get_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = 'Главное меню:'
        bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
        return 'HANDLE_MENU'
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)
    if command == 'Самовывоз':
        pizzeria_id = about_delivery
        pizzeria = get_entry(moltin_access_token, 'pizzeria', pizzeria_id)
        pizzeria_address = pizzeria['address']
        message = f'Ближайшая пиццерия находится по адресу: {pizzeria_address}. Ждем Вас!'
        keyboard = [
            [InlineKeyboardButton('В меню', callback_data='В меню;')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=reply_markup)
        return 'HANDLE_WAITING_DELIVERY'
    if command == 'Доставка':
        courier_chat_id, customer_chat_id, customer_latitude, customer_longitude = about_delivery.split(',')
        cart_items = get_cart_items(moltin_access_token, customer_chat_id)
        message = create_cart_description(cart_items)
        create_customer_address(moltin_access_token, 'customer_address',
                                'latitude', float(customer_latitude),
                                'longitude', float(customer_longitude))
        bot.send_message(text=message, chat_id=courier_chat_id)
        bot.send_location(courier_chat_id, latitude=customer_latitude, longitude=customer_longitude)
        chat_id = customer_chat_id
        title = "Оплатить"
        description = "Оплатить заказ"
        payload = "Custom-Payload"
        start_parameter = "test-payment"
        currency = "RUB"
        price = get_total_price(cart_items)
        prices = [LabeledPrice("Test", price * 100)]
        bot.sendInvoice(chat_id, title, description, payload,
                        provider_token, start_parameter, currency, prices)
        return 'HANDLE_USERS_REPLY'


def callback_alarm(bot, job):
    message = 'Приятного аппетита! *место для рекламы* \n\n' \
              '*сообщение что делать если пицца не пришла*'
    bot.send_message(chat_id=job.context, text=message)


def successful_payment_callback(bot, update, job_queue):
    update.message.reply_text("Оплата успешно выполнена! Спасибо!")
    job_queue.run_once(callback_alarm, 3600, context=update.message.chat_id)


def precheckout_callback(bot, update):
    query = update.pre_checkout_query
    if query.invoice_payload != 'Custom-Payload':
        bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=False,
                                      error_message="Что-то пошло не так...")
    else:
        bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)


def handle_users_reply(bot, update):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'HANDLE_WAITING_EMAIL': handle_waiting_email,
        'HANDLE_WAITING_ADDRESS': handle_waiting_address,
        'HANDLE_WAITING_DELIVERY': handle_waiting_delivery,
        'HANDLE_USERS_REPLY': handle_users_reply,
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(bot, update)
        db.set(chat_id, next_state)
    except Exception:
        logger.exception('Произошла ошибка:')


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.getenv('DATABASE_PASSWORD')
        database_host = os.getenv('DATABASE_HOST')
        database_port = os.getenv('DATABASE_PORT')
        _database = redis.Redis(host=database_host, port=int(database_port), password=database_password)
    return _database


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    env = Env()
    env.read_env()
    tg_token = env('TG_TOKEN')
    moltin_client_id = env('MOLTIN_CLIENT_ID')
    moltin_client_secret = env('MOLTIN_CLIENT_SECRET')
    tg_chat_id = env('TG_CHAT_ID')
    yandex_api_key = env('YANDEX_API_KEY')
    provider_token = env('PROVIDER_TOKEN')
    tg_bot = telegram.Bot(token=tg_token)
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(tg_bot, tg_chat_id))
    logger.info('Бот для логов запущен')

    updater = Updater(tg_token)
    dispatcher = updater.dispatcher

    while True:

        try:
            dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
            dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
            dispatcher.add_handler(CommandHandler('start', handle_users_reply))
            updater.dispatcher.add_handler(CallbackQueryHandler(handle_menu))
            handle_location = MessageHandler(Filters.location, handle_waiting_address)
            dispatcher.add_handler(handle_location)
            dispatcher.add_handler(
                MessageHandler(Filters.successful_payment, successful_payment_callback, pass_job_queue=True))
            dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
            updater.start_polling()
            logger.info('TG бот запущен')
            updater.idle()

        except Exception:
            logger.exception('Произошла ошибка:')
