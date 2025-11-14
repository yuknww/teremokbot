import random

from sqlalchemy.exc import IntegrityError

from app.bot.handlers.payment_info import send_payment_info
from app.bot.middlewares.logger import logger
from app.loader import bot
from app.db.models import Session, User, Registration, Child
from telebot import types
from psycopg2.errors import UniqueViolation


def registration_program(user: User, child: Child):
    db = Session()
    date_id = user.data["date_id"]
    program_id = user.data["program_id"]

    try:
        # Проверяем существующую регистрацию
        existing_reg = (
            db.query(Registration)
            .filter(
                Registration.child_id == child.id,
                Registration.date_id == date_id,
                Registration.program_id == program_id,
            )
            .first()
        )

        if existing_reg:
            logger.info(
                f"Ребёнок уже зарегистрирован child_id={child.id}, date_id={date_id}"
            )
            bot.send_message(user.telegram_id, f"Ребёнок уже зарегистрирован")
            return  # выходим, новые записи не создаём

        # Создаём новую регистрацию
        uuid = random.randint(10000000, 99999999)
        new_reg = Registration(
            child_id=child.id,
            date_id=date_id,
            program_id=program_id,
            ticket_code=str(uuid),
        )
        db.add(new_reg)
        db.commit()
        logger.info(f"Создана регистрация child_id={child.id}, ticket_code={uuid}")

        # Отправка информации о платеже
        send_payment_info(user, child, uuid)

    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError при добавлении в registrations: {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при регистрации: {e}")
    finally:
        db.close()
