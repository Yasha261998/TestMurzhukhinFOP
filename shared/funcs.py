import aiohttp
import random
import phonenumbers
import re
import json
import tldextract
from datetime import datetime
from urllib.parse import quote

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callbacks import ProxyEditingCallbackData
from .keyboards import demo_duration_keyboard, admin_duration_keyboard, start_keyboard, admin_start_keyboard
from .data import ukrainian_names, operators
from .config import (USERS_FILE, PROXIES_FILE, logger)


# Функція для генерації випадкового українського імені
def generate_name():
    return random.choice(ukrainian_names)


# Функція для генерації українського номера телефону з кодом оператора
def generate_phone_number():
    operator_name = random.choice(list(operators.keys()))
    operator_code = random.choice(operators[operator_name])
    phone_number = phonenumbers.parse(f"+380{operator_code}{random.randint(1000000, 9999999)}", None)
    return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)


# Функція для перевірки коректності URL
def is_valid_url(url):
    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return re.match(url_pattern, url) is not None


# Завантаження даних користувачів з JSON-файлу
def load_users_data(filepath='users.json'):
    try:
        with open(filepath, 'r') as file:
            users = json.load(file)
        return users
    except FileNotFoundError:
        return {}


def get_user_status(user_id):
    users = load_users_data()
    user_data = users.get(str(user_id))
    if user_data:
        return user_data.get('status')
    return None


# Функція для визначення клавіатури
def get_start_keyboard(user_id):
    users = load_users_data()  # Завантажуємо дані користувачів
    if users.get(str(user_id), {}).get('status') == 'admin':
        return admin_start_keyboard
    return start_keyboard


def get_duration_keyboard(user_id):
    users = load_users_data()  # Завантажуємо дані користувачів
    if users.get(str(user_id), {}).get('status') == 'admin':
        return admin_duration_keyboard
    return demo_duration_keyboard


# Альтернативна асинхронна перевірка URL за допомогою aiohttp
async def is_valid_url_aiohttp(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return response.status == 200
    except aiohttp.ClientError:
        return False


# Завантаження даних користувачів з файлу
def load_users():
    try:
        with open(USERS_FILE, 'r') as file:
            users = json.load(file)
            return {int(user_id): user_data for user_id, user_data in users.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Збереження даних користувачів до файлу
def save_users(users):
    with open(USERS_FILE, 'w') as file:
        json.dump(users, file, indent=4)


# Ініціалізація користувачів
users = load_users()


# Додавання нового користувача
def register_user(user_id):
    if user_id not in users:
        users[user_id] = {
            'id': user_id,
            'registration_date': str(datetime.now()),
            'status': 'demo',
            'applications_sent': 0,
            'applications_per_url': {}
        }
        save_users(users)


# Функція для отримання домену з URL
def extract_domain(url: str) -> str:
    extracted = tldextract.extract(url)
    domain = f"{extracted.domain}.{extracted.suffix}"
    return domain


# Функція для перевірки чи користувач досяг ліміту заявок
def is_demo_limit_reached(user_id):
    user_data = users.get(user_id, {})
    return user_data.get('status') == 'demo' and user_data.get('applications_sent', 0) >= 50


# Завантаження даних проксі у словник
def load_proxies():
    try:
        with open(PROXIES_FILE, 'r') as file:
            proxies = json.load(file)
            # Перетворюємо об'єкт проксі на словник для зручного доступу за ім'ям
            return {name: proxy for name, proxy in proxies.get('proxies', {}).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Завантаження даних проксі з json файлу
def open_proxy_json():
    try:
        with open(PROXIES_FILE, 'r') as file:
            proxies = json.load(file)
            return proxies
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_proxy_url(proxy_data: dict):
    url = f"http://{quote(proxy_data['login'])}:{quote(proxy_data['password'])}@{proxy_data['ip']}:{proxy_data['port']}"
    return url


# Функція для перевірки коректності введеного проксі
def is_valid_proxy(proxy):
    proxy_pattern = re.compile(
        r'^(?P<host>(?:\d{1,3}\.){3}\d{1,3}|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}),'
        r'(?P<port>([1-9]\d{0,4}|[1-5]\d{5})),'
        r'(?P<username>[^\s,]+),'
        r'(?P<password>[^\s,]+)$'
    )
    return re.match(proxy_pattern, proxy) is not None


# Функція для генерації повідомлення про проксі з інформацією про його статус та налаштування.
def generate_proxy_message(proxy_id, proxy_data):
    status = "Ввімкнене" if proxy_data['use_proxy'] else "Вимкнене"
    return (
        f"Проксі {proxy_id}:\n"
        f"Статус: {status}\n"
        f"IP: {proxy_data['ip']}\n"
        f"Порт: {proxy_data['port']}\n"
        f"Логін: {proxy_data['login']}\n"
        f"Пароль: {proxy_data['password']}\n"
    )


# Функція для генерації інлайн-клавіатури для проксі з кнопками для управління статусом та редагуванням.
def generate_proxy_inline_keyboard(proxy_id, use_proxy):
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="Вимкнути" if use_proxy else "Ввімкнути",
            callback_data=ProxyEditingCallbackData(action="toggle", proxy_id=proxy_id).pack()
        ),
        InlineKeyboardButton(
            text="Редагувати",
            callback_data=ProxyEditingCallbackData(action="edit", proxy_id=proxy_id).pack()
        ))
    builder.row(
        InlineKeyboardButton(
            text="Видалити дані",
            callback_data=ProxyEditingCallbackData(action="delete_data", proxy_id=proxy_id).pack()
        ))
    builder.row(
        InlineKeyboardButton(
            text="Видалити проксі",
            callback_data=ProxyEditingCallbackData(action="delete_proxy", proxy_id=proxy_id).pack()
        ))
    return builder.as_markup()


# Функція для перевірки працездатності проксі за заданими параметрами.
async def is_proxy_working(ip, port, login, password):
    proxy_url = f'http://{quote(login)}:{quote(password)}@{ip}:{port}'
    url = 'https://httpbin.org/ip'  # Тестовый URL для перевiрки проксi

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), timeout=timeout) as session:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
            }

            async with session.get(url, proxy=proxy_url, headers=headers) as response:

                if response.status == 200:
                    return True
                else:
                    logger.error(f"Returned status {response.status} for {proxy_url}")
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"Client error with proxy {proxy_url}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with proxy {proxy_url}: {str(e)}")
            return False


# Функція для підготовки повідомлень про проксі з інформацією та інлайн-клавіатурами.

async def prepare_proxy_messages(proxies_dict: dict) -> list:
    proxy_messages = []
    for proxy_id, proxy_data in proxies_dict.items():
        text = generate_proxy_message(proxy_id, proxy_data)
        keyboard = generate_proxy_inline_keyboard(proxy_id, proxy_data['use_proxy'])
        proxy_messages.append((text, keyboard))
    return proxy_messages


# Функція для оновлення данных проксi
def update_proxy_data(proxy_id, ip, port, login, password, proxies=None):
    if proxies is None:
        proxies = open_proxy_json()

    if proxy_id in proxies['proxies']:
        proxies['proxies'][proxy_id]['ip'] = ip
        proxies['proxies'][proxy_id]['port'] = port
        proxies['proxies'][proxy_id]['login'] = login
        proxies['proxies'][proxy_id]['password'] = password

        with open(PROXIES_FILE, 'w') as file:
            json.dump(proxies, file, indent=4)


# Функція для створення нового проксі
def insert_proxy_data(ip, port, login, password):
    proxies = open_proxy_json()

    proxy_id = "1"
    for proxy_id_int in range(1, len(proxies['proxies']) + 2):
        if str(proxy_id_int) not in proxies['proxies']:
            proxy_id = str(proxy_id_int)
            break

    proxies['proxies'][proxy_id] = {}
    proxies['proxies'][proxy_id]["use_proxy"] = False

    update_proxy_data(proxy_id, ip, port, login, password, proxies)
    return proxy_id


# Функція для перемикання стану використання проксі за вказаним ідентифікатором.
def toggle_proxy_state(proxy_id):
    proxies = open_proxy_json()
    if proxy_id in proxies['proxies']:
        current_state = proxies['proxies'][proxy_id]['use_proxy']
        new_state = not current_state

        proxies['proxies'][proxy_id]['use_proxy'] = new_state
        with open(PROXIES_FILE, 'w') as file:
            json.dump(proxies, file, indent=4)


# Функція видалення даних з проксі
def delete_proxy_data(proxy_id):
    proxies = open_proxy_json()
    if proxy_id in proxies['proxies']:
        proxies['proxies'][proxy_id]['ip'] = ""
        proxies['proxies'][proxy_id]['port'] = ""
        proxies['proxies'][proxy_id]['login'] = ""
        proxies['proxies'][proxy_id]['password'] = ""
        proxies['proxies'][proxy_id]['type'] = ""

        with open(PROXIES_FILE, 'w') as file:
            json.dump(proxies, file, indent=4)


# Функція видалення проксі та новий порядок
def delete_proxy(proxy_id):
    data = open_proxy_json()

    if proxy_id in data["proxies"]:
        del data["proxies"][proxy_id]

    proxies = data["proxies"]
    keys = list(proxies.keys())
    for i in range(len(keys)):
        new_key = str(i + 1)
        proxies[new_key] = proxies.pop(keys[i])

    with open('proxies.json', 'w') as file:
        json.dump(data, file, indent=4)
