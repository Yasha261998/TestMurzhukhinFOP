import asyncio
import random

import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urlunsplit

from .config import (user_request_counter, logger)
from .funcs import generate_name, generate_phone_number, is_proxy_working, load_proxies, get_proxy_url, get_user_agent


async def send_request_to_form(url, user_id):
    logger.info(f"Запит до форми: {url}")
    # Отримання User Agent
    user_agent = get_user_agent()

    # Формування проксі
    all_proxies = load_proxies()  # Всi проксi

    enabled_proxies = [proxy for proxy in all_proxies.values() if proxy['use_proxy']]
    proxies = []

    if enabled_proxies:
        attempts_user_agents = 2
        for proxy in enabled_proxies:
            if await is_proxy_working(
                    ip=proxy['ip'],
                    port=proxy['port'],
                    login=proxy['login'],
                    password=proxy['password'],
                    user_agent=user_agent
            ):
                proxies.append(get_proxy_url(proxy))
            else:
                logger.error(f"Проксі http://{proxy['login']}:{proxy['password']}@{proxy['ip']}:{proxy['port']} недоступне")

        if not proxies:
            logger.error("Всі проксі недоступні. Відправка буде виконана без проксі.")

    logger.info(proxies)
    attempts = 3  # Загальна кількість спроб
    timeout = 15  # Таймаут для запитів

    for attempt in range(attempts):
        proxy_url = random.choice(proxies) if proxies else None
        logger.info(f"Використання запиту з проксі: {proxy_url}" if proxy_url else "Використання запиту без проксі.")

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            try:
                logger.info(f"Надсилаємо GET запит до: {url}")
                headers = {
                    'User-Agent': user_agent
                }

                async with session.get(url, proxy=proxy_url, headers=headers, timeout=timeout) as response:
                    logger.info(f"Отримано відповідь: {response.status}")
                    if response.status != 200:
                        if attempt < attempts - 1:  # Якщо це не остання спроба
                            logger.warning(
                                "Сайт недоступний. Спробуємо ще раз...")
                            await asyncio.sleep(10)  # Затримка перед повтором
                            continue  # Повертаємось до початку циклу
                        return f"Сайт недоступний. Код статусу: {response.status}."

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    form = soup.find('form')

                    if not form:
                        if attempt < attempts - 1:  # Якщо це не остання спроба
                            logger.warning(f"Форма не знайдена. Спроба {attempt+1}")
                            await asyncio.sleep(2)  # Затримка перед повтором
                            continue  # Повертаємось до початку циклу
                        return "Форма не знайдена на сторінці."

                    action = form.get('action')
                    if action:
                        if not action.startswith('http'):
                            # base_url = user_urls[user_id]
                            base_url = url
                            split_url = urlsplit(base_url)
                            base_url_without_query = urlunsplit(
                                (split_url.scheme, split_url.netloc, split_url.path.rstrip('/') + '/', '', ''))
                            action = f"{base_url_without_query}{action.lstrip('/')}"  #

                        logger.info(f"Формований URL дії: {action}")

                    data = {}
                    inputs = form.find_all('input')
                    for input_tag in inputs:
                        input_name = input_tag.get('name')
                        input_type = input_tag.get('type')

                        if input_type == 'name' or input_name == 'name':
                            data[input_name] = generate_name()

                        elif input_type == 'tel' or input_name == 'phone' or input_name == 'tel':
                            data[input_name] = generate_phone_number()

                        elif input_type == 'checkbox':
                            data[input_name] = 'on'

                    selects = form.find_all('select')
                    for select in selects:
                        select_name = select.get('name')
                        options = select.find_all('option')
                        valid_options = [option for option in options if option.get('value')]
                        if valid_options:
                            selected_option = random.choice(valid_options).get('value')
                            data[select_name] = selected_option

                    logger.info(f"Дані, які будуть надіслані: {data}")

                    for post_attempt in range(attempts):
                        async with session.post(action, data=data, proxy=proxy_url, timeout=timeout) as post_response:
                            if post_response.status == 200:
                                logger.info(
                                    f"Запит на {action} успішно надіслано.")
                                user_request_counter[user_id][url] += 1
                                return None  # Успішно відправлено
                            else:
                                logger.error(f"Помилка при відправці: {post_response.status}")
                                if post_attempt < attempts - 1:  # Якщо це не остання спроба
                                    # Затримка 10 секунд перед повтором
                                    await asyncio.sleep(10)
                                else:
                                    return "Не вдалося відправити заявку."

            except asyncio.TimeoutError:
                logger.error(f"Запит до {url} перевищив таймаут.")
                if attempt < attempts - 1:  # Якщо це не остання спроба
                    await asyncio.sleep(10)  # Затримка перед повтором
                else:
                    return "Запит перевищив таймаут."

            except aiohttp.ClientError as e:
                print(e.args)
                logger.error(f"Помилка при використанні проксі: {e}")
                if attempt < attempts - 1:  # Якщо це не остання спроба
                    # Затримка 10 секунд перед повтором
                    await asyncio.sleep(10)
                else:
                    return "Проблема з проксі."

    return None  # Успішно відправлено