# Telegram Bot

## Залежності

- Python 3.10+
- [Poetry](https://python-poetry.org/) для управління залежностями

## Запуск бота

1. *Встановлення залежностей (тільки при першому запуску)*:

   ```bash
   poetry install
   ```
   
2. *Створення .env файлу та заповнення інформації*:

   ```bash
   cp .env.example .env
   ```

3. *Активація робочого середовища*:

   ```bash
   poetry shell
   ```

4. *Запуск бота*:

   ```bash
   python bot.py
   ```