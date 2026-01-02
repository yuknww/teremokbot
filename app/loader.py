import telebot
from app.core import config
from telebot import apihelper

# Увеличить таймаут для всех запросов
apihelper.READ_TIMEOUT = 45  # можно увеличить до 45-60
apihelper.CONNECT_TIMEOUT = 20

# Включить retry для определенных методов
apihelper.RETRY_ON_ERROR = True
apihelper.MAX_RETRIES = 3  # 3 попытки лучше чем 2

# Дополнительно можно настроить
apihelper.SESSION_TIME_TO_LIVE = 300  # 5 минут жизни сессии
apihelper.proxy = None  # если не используете прокси

bot = telebot.TeleBot(token=config.BOT_TOKEN)

# Опционально: настроить polling параметры если используете
bot.skip_pending = True  # пропустить ожидающие сообщения при старте
