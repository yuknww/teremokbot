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


from datetime import datetime


def get_event_message(date_id: int, session: Session):
    try:
        date_slot = session.query(DateSlot).filter(DateSlot.id == date_id).first()
        if not date_slot:
            return "Дата не найдена"

        # увеличиваем booked_count
        date_slot.booked_count += 1
        session.commit()

        # дата (строка 'YYYY-MM-DD')
        dt_str = date_slot.date
        dt = datetime.strptime(dt_str, "%Y-%m-%d")  # превращаем в datetime
        day = dt.day
        month = RUS_MONTHS[dt.month]

        # время (строка 'HH:MM' или 'HH:MM:SS')
        t_str = date_slot.time
        # приводим к datetime.time
        t = (
            datetime.strptime(t_str, "%H:%M").time()
            if len(t_str) == 5
            else datetime.strptime(t_str, "%H:%M:%S").time()
        )
        time_str = t.strftime("%H:%M")  # форматируем для сообщения

        message = f"Ждём вас на Масленицу {day:02d} {month}, в {time_str}"
        return message
    except Exception as e:
        logger.error(f"Возникла ошибка в определении даты и времени {e}")
        return None


def process_successful_payment(data):
    db = Session()
    try:
        logger.info("Start successful payment")

        uuid = str(data["OrderId"])

        # Получаем регистрацию сразу со связанными объектами
        reg: Registration = (
            db.query(Registration).filter(Registration.ticket_code == uuid).first()
        )

        if not reg:
            logger.error(f"Registration with ticket {uuid} not found")
            return

        # Через relationship
        child: Child = reg.child  # child_id → child
        user: User = child.user  # child → user

        user_id = int(user.telegram_id)

        # Обновляем статус оплаты
        reg.payment_status = "completed"
        db.commit()

        # Обновляем состояние пользователя
        update_user_state(db=db, telegram_id=user_id, state="registered")

        # Генерируем билет
        path_ticket = qrcodegen(uuid)
        try:
            with open(path_ticket, "rb") as photo:
                bot.send_photo(user_id, photo)
                logger.info(f"user_id: {user_id} отправлен билет {uuid}")
        except Exception as e:
            for admin in ADMIN_ID:
                bot.send_message(
                    admin, f"Ошибка отправки билета для пользователя {user_id}"
                )
            logger.error(f"Возникла ошибка при отправке билета {e} {e.args}")
            bot.send_message(
                user_id,
                "Возникла проблема с загрузкой билета, обратитесь пожалуйста к администратору @yuknww\n\n"
                "Или введите /start и нажмите кнопку Мои билеты",
            )
        finally:
            # Сообщение пользователю
            text = (
                f"Всё готово!\n"
                f"Сохраните свой билет — его нужно будет показать на входе\n\n"
                f"‼️*Детям нужно взять сменную обувь, взрослым - бахилы*"
                f"{get_event_message(date_id=reg.date_id, session=db)}\n\n"
                f"🔔 Информация о мероприятии в нашем Telegram-канале: @teremok_vyazma\n\n"
                f"❓ Если остались вопросы, можно написать администратору — @yuknww\n\n"
            )
            bot.send_message(user_id, text)
            logger.info(f"user_id: {user_id} отправлена финальная информация")

            # Текст для админов
            new_reg_text = (
                f"Новая регистрация:\n\n"
                f"Имя: {user.full_name}\n"
                f"Имя ребёнка: {child.child_name}\n"
                f"Возраст: {child.birth_date}\n"
                f"Телефон: {user.phone}\n"
                f"ID: {user.telegram_id}\n"
                f"Код регистрации: {uuid}"
            )

            for admin in ADMIN_ID:
                bot.send_message(admin, new_reg_text)

            logger.info(f"Регистрация подтверждена: user_id={user_id}, uuid={uuid}")

    finally:
        db.close()
