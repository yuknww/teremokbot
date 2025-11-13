import time
from app.loader import bot
from app.bot import handlers
from app.db.models import Base, engine

if __name__ == "__main__":
    time.sleep(5)
    Base.metadata.create_all(bind=engine)
    bot.infinity_polling()
