import telebot
from app.core import config

bot = telebot.TeleBot(token=config.BOT_TOKEN)
