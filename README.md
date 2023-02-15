# Pizza shop in telegram (bot)

Посмотрите пример работающего телеграм-бота по [ссылке](https://t.me/PizzaShop21Bot).
## Установка и настройки:
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

`PROVIDER_TOKEN` - Токен для выставления счетов. Получить через [BotFather](https://telegram.me/BotFather).

*`PRODUCTS_PATH` - Путь до json-файла с данными продуктов.

*`PIZZERIAS_PATH` - Путь до json-файла с данными пиццерий.

`PAGE_ACCESS_TOKEN` - Токен для страницы бота в Facebook (воспользуйтесь [инструкцией](https://dvmn.org/encyclopedia/api-docs/how-to-get-facebook-api/))

`VERIFY_TOKEN` - Токен для валидации вебхука в Facebook (воспользуйтесь [инструкцией](https://dvmn.org/encyclopedia/api-docs/how-to-get-facebook-api/))

## Запуск телеграм-бота:
Введите команду:
```commandline
python3 tg_bot.py
```

## Настройка и запуск фейсбук-бота на удаленном сервере:
* Подключитесь к серверу, загрузите код, установите виртуальное окружение и установите зависимости.
* Перейдите в директорию для создания демона:
```commandline
cd /etc/systemd/system
```
* Создайте демона `{название_файла}.service`.
* Скопируйте содержимое и вставьте в созданный файл, заменив пути до директорий на свои:
```
[Unit]
Description=Фейсбук-бот по продаже пиццы.

[Service]
WorkingDirectory={путь_до_директории_с_проектом}
ExecStart={путь_до_директории_с_проектом}/venv/bin/gunicorn -w 2 -b 127.0.0.1:8090 fb-bot:app
Restart=always

[Install]
WantedBy=multi-user.target

```
* Демон создан, запустите его:
```commandline
systemctl start {название_демона}.service
```
* Чтобы служба запускалась при загрузке системы, используйте команду:
```commandline
systemctl enable {название_демона}.service
```
* Уcтановите nginx:
```commandline
sudo apt install nginx
```
* Перейдите в директорию с конфигами nginx:
```commandline
cd /etc/nginx/sites-enabled/
```
* Удалите дефолдный конфиг и ссздайте свой с любым названием:
```
server {
  server_name {ваш домен}; # замените домен на свой
  location / {
    include '/etc/nginx/proxy_params';
    proxy_pass http://127.0.0.1:8090/;  # ! порт должен совпадать с тем, что указан в демоне
  }
```
* [Уставите Certbot](https://certbot.eff.org/lets-encrypt/). Выберите нужные вам варианты в зависимости от вашей системы.
* Запустите nginx:
```commandline
systemctl start nginx.service
```
* Чтобы служба запускалась при загрузке системы, используйте команду:
```commandline
systemctl enable nginx.service
```
* Воспользуйтесь [инструкцией](https://dvmn.org/encyclopedia/api-docs/how-to-get-facebook-api/) для подключения бота к вашей странице на Facebook.
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
### Скрипт `update_db.py`:
##### Запуск скрипта вручную:
```commandline
python3 update_db.py
```
При первом запуске скрипт скачает данные с Moltin и загрузит в базу данных Pedis.

При последующих запусках скрипт будет проверять Moltin на обновление данных, если они изменились, то обновит данные в Redis.
##### Автоматический запуск скрипта на удаленном сервере:
* Перейдите в следующую директорию:
```commandline
cd /etc/systemd/system
```
* Создайте демона с содержимым (например `update-db.service`):
```
[Service]
WorkingDirectory={путь_до_папки_с_проектом}
ExecStart={путь_до_папки_с_проектом}/venv/bin/python3.9 update_db.py
Restart=on-abort

[Install]
WantedBy=multi-user.target
```
* Создайте таймер, который будет запускать демона раз в пять минут,
тем самым проверять и при необходимости обновлять БД (например `update-db.timer`, имя должно совпадать с демоном):
```
[Unit]
Description=Таймер для обновления БД в fb-bot

[Timer]
OnBootSec=300
OnUnitActiveSec=5min

[Install]
WantedBy=multi-user.target
```