import time

from app.bot.utils.qr import qrcodegen
from app.loader import bot
from app.bot import handlers
from app.db.models import Base, engine
from app.bot.middlewares.logger import logger

if __name__ == "__main__":
    time.sleep(5)
    Base.metadata.create_all(bind=engine)
    logger.info("Бот запущен")
    bot.infinity_polling()
