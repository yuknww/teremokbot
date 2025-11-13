import os
import telebot
from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit("Переменные окружения не загружены т.к отсутствует файл .env")
else:
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHECK_REG_TOKEN = os.getenv("CHECK_REG_TOKEN")
TERMINAL_KEY = os.getenv("TERMINAL_KEY")
PASSWORD = os.getenv("PASSWORD")

ADMIN_ID = [734641318]
