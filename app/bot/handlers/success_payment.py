import datetime

from app.bot.middlewares.logger import logger
from app.bot.utils.qr import qrcodegen
from app.core.config import ADMIN_ID
from app.db.crud import update_user_state
from app.loader import bot
from app.db.models import Registration, Session, Child, User, DateSlot

RUS_MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def get_event_message(date_id: int, session: Session):
    try:
        date_slot = session.query(DateSlot).filter(DateSlot.id == date_id).first()
        date_slot.booked_count += 1
        session.commit()
        if not date_slot:
            return "Дата не найдена"

        # дата
        dt = date_slot.date  # datetime.date
        if isinstance(dt, str):
            dt = datetime.strptime(dt, "%Y-%m-%d").date()
        day = dt.day
        month = RUS_MONTHS[dt.month]

        # время
        t = date_slot.time  # datetime.time
        time_str = t.strftime("%H:%M")  # форматируем как 'HH:MM'

        message = f"Ждём вас в Теремке Новогодних Чудес {day:02d} {month}, в {time_str}"
        return message
    except Exception as e:
        logger.error(f"Возникла ошибка в опреедлнии даты и времени {e}")
        return None


def process_successful_payment(data):
    db = Session()
    try:
        logger.info(f"Start successful payment")
        uuid = str(data["OrderId"])
        reg: Registration = (
            db.query(Registration).filter(Registration.ticket_code == uuid).first()
        )
        child = db.query(Child).filter(Child.id == reg.child_id).first()
        user = db.query(User).filter(User.id == Child.user_id).first()
        user_id = int(user.telegram_id)

        reg.payment_status = "completed"

        update_user_state(db=db, telegram_id=user_id, state="registered")
        path_ticket = qrcodegen(uuid)

        with open(path_ticket, "rb") as photo:
            bot.send_photo(user_id, photo)
            logger.info(f"user_id: {user_id} отправлен билет {uuid}")

        text = (
            f"Всё готово!\n"
            f"Сохраните свой билет, его нужно будет показать на входе\n\n"
            f"{get_event_message(date_id=reg.date_id, session=db)}\n\n"
            f"🔔Информация о мероприятии в нашем Telegram-канале: @teremok_vyazma\n\n"
            f"❓Если у тебя остались вопросы, можешь написать администратору - @yuknww\n\n"
        )
        bot.send_message(user_id, text)
        logger.info(
            f"user_id: {user_id} отправлена информация после подтверждения регистрации"
        )

        new_reg_text = (
            f"Новая регистрация:\n\n"
            f"Имя: {user.full_name}\n"
            f"Имя ребёнка: {child.child_name}\n"
            f"Возраст: {child.birth_date}\n"
            f"Телефон: {user.phone}\n"
            f"ID: {user.telegram_id}"
            f"Код регистрации: {uuid}"
        )

        for admin in ADMIN_ID:
            bot.send_message(admin, new_reg_text)
        logger.info(
            f"Регистрация user_id: {user_id} с uuid: {uuid} подтверждена и внесена в таблицу"
        )
    finally:
        db.close()
