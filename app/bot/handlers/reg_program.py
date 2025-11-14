import random

from app.bot.handlers.payment_info import send_payment_info
from app.bot.middlewares.logger import logger
from app.loader import bot
from app.db.models import Session, User, Registration, Child
from telebot import types


def registration_program(user: User, child: Child):
    db = Session()
    date_id = user.data["date_id"]
    program_id = user.data["program_id"]
    uuid = random.randint(10000000, 99999999)
    try:
        new_reg = Registration(
            child_id=child.id,
            date_id=date_id,
            program_id=program_id,
            ticket_code=str(uuid),
        )
        db.add(new_reg)
        db.commit()
    except Exception as e:
        logger.error(f"Возникла ошибка при добавлении в таблицу Registrations {e}")

    try:
        send_payment_info(user, child)
    except Exception as e:
        logger.error(f"Возникла ошибка при отправке информации о платеже {e}")
