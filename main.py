from app.loader import bot
from app.bot import handlers
from app.db.models import Base, engine
from app.bot.middlewares.logger import logger

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    logger.info("Бот запущен")
    bot.infinity_polling()
