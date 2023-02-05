# Pizza shop in telegram (bot)
## Установка, настройки и запуск:
* Скачайте код.
* Установите зависимости:
```
pip install -r requirements.txt
```
* Запишите переменные окружения в файле .env в формате КЛЮЧ=ЗНАЧЕНИЕ (звездочкой отмечены необязательные):

`MOLTIN_CLIENT_ID` - Client id на [Moltin](https://euwest.cm.elasticpath.com/).

`MOLTIN_CLIENT_SECRET` - Client server на [Moltin](https://euwest.cm.elasticpath.com/).

`TG_TOKEN` - Телеграм токен. Получить у [BotFather](https://telegram.me/BotFather).

`DATABASE_HOST` - Адрес базы данных redis.

`DATABASE_PORT` - Порт базы данных redis.

`DATABASE_PASSWORD` - Пароль базы данных redis.

`TG_CHAT_ID` - ID чата в телеграм, в который будут приходить логи.

`YANDEX_API_KEY` - [API Яндекс-геокодера](https://developer.tech.yandex.ru/services/).

`PROVIDER_TOKEN` - токен для выставления счетов. Получить через [BotFather](https://telegram.me/BotFather).

*`PRODUCTS_PATH` - путь до json-файла с данными продуктов.

*`PIZZERIAS_PATH` - путь до json-файла с данными пиццерий.

* Запустите бота:
```commandline
python3 tg_bot.py
```

### Скрипт `upload_data.py`:
Загружает данные на [Moltin](https://euwest.cm.elasticpath.com/),
создает модели `Pizzeria` (с полями: Address, Alias, Longitude, Latitude, Courier id)
и `Customer Address` (с полями: Latitude, Longitude).

Для запуска вызовите команду:
```commandline
python3 upload_data.py
```
Скрипт берет данные из двух json-файлов:

* Файл с данными продуктов (по умолчанию `products.json`)

Пример содержимого:
```json
[
    {
        "name": "Чизбургер-пицца",
        "description": "мясной соус болоньезе, моцарелла, лук, соленые огурчики, томаты, соус бургер",
        "product_image": {
            "url": "https://dodopizza-a.akamaihd.net/static/Img/Products/Pizza/ru-RU/1626f452-b56a-46a7-ba6e-c2c2c9707466.jpg"
        },
        "price": 395
    },
    {
        "name": "Крэйзи пепперони ",
        "description": "Томатный соус, увеличенные порции цыпленка и пепперони, моцарелла, кисло-сладкий соус",
        "product_image":{
            "url": "https://dodopizza-a.akamaihd.net/static/Img/Products/Pizza/ru-RU/7aa1638e-1bee-4162-a2df-6bbaf683a486.jpg"
        },
        "price": 425
    }
]
```
* Файл с данными о пиццериях (по умолчанию `pizzerias.json`)

Пример содержимого:
```json
[
    {
        "alias": "Афимолл",
        "address": {
           "full": "Москва, набережная Пресненская дом 2"
        },
        "coordinates": {
            "lat": "55.749299",
            "lon": "37.539644"
        },
        "courier_id": 1045671239
    },
    {
        "alias": "Ясенево",
        "address": {
            "full": "Москва, проспект Новоясеневский дом вл7"
        },
        "coordinates": {
            "lat": "55.607489",
            "lon": "37.532367"
        },
        "courier_id": 1045671242
    }
]
```
