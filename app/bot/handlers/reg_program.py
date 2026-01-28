import random

from sqlalchemy.exc import IntegrityError

from app.bot.handlers.payment_info import send_payment_info
from app.bot.middlewares.logger import logger
from app.db.crud import update_user_state
from app.loader import bot
from app.db.models import Session, User, Registration, Child
from telebot import types
from psycopg2.errors import UniqueViolation


def registration_program(user: User, child: Child):
    db = Session()

    if not user.phone:
        bot.send_message(user.telegram_id, "Пожалуйста, укажите номер телефона:")
        update_user_state(db=db, telegram_id=user.telegram_id, state="parent_phone")
        db.close()
        return

    if not user.email:
        bot.send_message(user.telegram_id, "Пожалуйста, укажите ваш Email:")
        update_user_state(db=db, telegram_id=user.telegram_id, state="parent_email")
        db.close()
        return

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
            if existing_reg.payment_status != "completed":
                uuid = random.randint(10000000, 99999999)
                existing_reg.ticket_code = uuid
                db.commit()
                send_payment_info(user, child, uuid)
                return
            logger.info(
                f"user_id={user.telegram_id} Ребёнок уже зарегистрирован child_id={child.id}, date_id={date_id}"
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
        logger.info(f"user_id={user.telegram_id} Создана регистрация child_id={child.id}, ticket_code={uuid}")

        # Отправка информации о платеже
        send_payment_info(user, child, uuid)

    except IntegrityError as e:
        db.rollback()
        logger.error(f"user_id={user.telegram_id} IntegrityError при добавлении в registrations: {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"user_id={user.telegram_id} Ошибка при регистрации: {e}")
    finally:
        db.close()
