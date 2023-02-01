import logging
import os

import redis
import telegram
from environs import Env
from geopy import distance
from requests.exceptions import HTTPError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, Updater)

from format_message import create_cart_description, create_product_description
from geo_helpers import fetch_coordinates, get_nearest_pizzeria
from log_helpers import TelegramLogsHandler
from moltin_helpers import (add_product_to_cart, create_customer,
                            delete_product_from_cart, get_all_products,
                            get_cart_items, get_image_by_id,
                            get_moltin_access_token, get_product_by_id)

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
        current_coordinates = fetch_coordinates(yandex_api_key, address)
        if not current_coordinates:
            bot.send_message(text='Некорректный адрес, повторите попытку:', chat_id=update.message.chat_id)
            return 'HANDLE_WAITING_ADDRESS'
    else:
        if update.edited_message:
            message = update.edited_message
        else:
            message = update.message
        current_coordinates = (message.location.latitude, message.location.longitude)
    nearest_pizzeria = get_nearest_pizzeria(current_coordinates, moltin_client_id, moltin_client_secret, flow_slug)
    pizzeria_distance = distance.distance((nearest_pizzeria.get('latitude'), nearest_pizzeria.get('longitude')), current_coordinates)
    if pizzeria_distance <= 0.5:
        message = f'Вы можете забрать заказ по адресу: {nearest_pizzeria["address"]}, или доставим бесплатно'
    elif pizzeria_distance <= 5:
        message = f'Вы можете забрать заказ по адресу: {nearest_pizzeria["address"]}, или доставим за 100 рублей'
    elif pizzeria_distance <= 20:
        message = f'Вы можете забрать заказ по адресу: {nearest_pizzeria["address"]}, или доставим за 300 рублей'
    else:
        message = f'Вы можете забрать заказ по адресу: {nearest_pizzeria["address"]}. К сожалению, мы не можем доставить по вашему адресу'
    bot.send_message(text=message, chat_id=update.message.chat_id)
    return 'HANDLE_WAITING_ADDRESS'


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
    flow_slug = env('FLOW_SLUG', 'pizzeria')
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
            updater.start_polling()
            logger.info('TG бот запущен')
            updater.idle()

        except Exception:
            logger.exception('Произошла ошибка:')
