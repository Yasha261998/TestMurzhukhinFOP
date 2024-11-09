import os
import logging
from dotenv import load_dotenv

# Define the path to the .env file
env_path = '.env'

# Load the environment variables from the .env file
load_dotenv(env_path)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_FILE = 'users.json'
PROXIES_FILE = 'proxies.json'


def get_env_value(key):
    if key in os.environ:
        return os.environ[key]
    raise KeyError(f"Environment variable '{key}' not found")


API_TOKEN = get_env_value('API_TOKEN')

# Глобальні змінні для зберігання стану бота
user_state = {}
user_urls = {}
active_sessions = {}    # Активні сесії (посилання)
active_sending = {}     # Маркер активної відправки
active_tasks = {}       # Активні задачі
user_request_counter = {}
user_durations = {}     # Тривалість для кожного користувача
user_frequencies = {}   # Частота для кожного користувача

# Список вибору частоти відправки
frequency_options = ["Без затримки 🚀", "1 заявка в 10 секунд ⏳", "1 заявка в 10 хвилин ⌛", "1 заявка в 60 хвилин ⌛"]

# Список вибору тривалості відправки
duration_options = ["1 хвилина ⏳", "15 хвилин ⏳", "30 хвилин ⏳", "1 година ⏳", "3 години ⏳", "Необмежено ⏳"]
