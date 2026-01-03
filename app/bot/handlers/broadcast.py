import time
from sqlalchemy import distinct
from telebot.types import Message

from app.loader import bot
from app.core.config import ADMIN_ID
from app.db.models import (
    Session,
    User,
    Child,
    Registration,
)

# -------------------------------------------------
# ВСПОМОГАТЕЛЬНОЕ
# -------------------------------------------------


def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_ID


# -------------------------------------------------
# РАССЫЛКА
# -------------------------------------------------


def broadcast_to_parents_by_date(
    date_id: int,
    text: str,
    delay: float = 0.3,
):
    session = Session()

    try:
        parents = (
            session.query(distinct(User.telegram_id))
            .join(Child, Child.user_id == User.id)
            .join(Registration, Registration.child_id == Child.id)
            .filter(Registration.date_id == date_id)
            .all()
        )

        telegram_ids = [row[0] for row in parents]

        sent = 0
        errors = 0

        for tg_id in telegram_ids:
            try:
                bot.send_message(tg_id, text)
                sent += 1
                time.sleep(delay)
            except Exception as e:
                errors += 1
                print(f"[BROADCAST ERROR] {tg_id}: {e}")

        print(f"[BROADCAST DONE] date_id={date_id} | " f"sent={sent} | errors={errors}")

    finally:
        session.close()


# -------------------------------------------------
# ХЕНДЛЕРЫ АДМИНКИ
# -------------------------------------------------


@bot.message_handler(commands=["broadcast"])
def admin_broadcast_start(message: Message):
    if not is_admin(message):
        bot.reply_to(message, "Нет доступа")
        return

    msg = bot.send_message(message.chat.id, "Введи date_id для рассылки:")
    bot.register_next_step_handler(msg, admin_broadcast_get_date)


def admin_broadcast_get_date(message: Message):
    if not is_admin(message):
        return

    try:
        date_id = int(message.text)
    except ValueError:
        msg = bot.send_message(
            message.chat.id, "date_id должен быть числом. Попробуй ещё раз:"
        )
        bot.register_next_step_handler(msg, admin_broadcast_get_date)
        return

    msg = bot.send_message(
        message.chat.id, "Теперь отправь текст сообщения для родителей:"
    )
    bot.register_next_step_handler(
        msg,
        admin_broadcast_get_text,
        date_id,
    )


def admin_broadcast_get_text(message: Message, date_id: int):
    if not is_admin(message):
        return

    text = message.text.strip()

    if not text:
        bot.send_message(
            message.chat.id, "Текст не может быть пустым. Отправь сообщение ещё раз:"
        )
        bot.register_next_step_handler(
            message,
            admin_broadcast_get_text,
            date_id,
        )
        return

    bot.send_message(message.chat.id, f"Запускаю рассылку для date_id={date_id}...")

    broadcast_to_parents_by_date(
        date_id=date_id,
        text=text,
    )

    bot.send_message(message.chat.id, "Рассылка завершена")
