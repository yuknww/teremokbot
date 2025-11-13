import os
from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit("Переменные окружения не загружены т.к отсутствует файл .env")
else:
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = "postgresql+psycopg2://admin:admin@db:5432/teremok_db"
CHECK_REG_TOKEN = os.getenv("CHECK_REG_TOKEN")
TERMINAL_KEY = os.getenv("TERMINAL_KEY")
PASSWORD = os.getenv("PASSWORD")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")


ADMIN_ID = [734641318]
