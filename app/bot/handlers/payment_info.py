from app.loader import bot
from app.bot.middlewares.logger import logger
from app.db.models import User, Registration, Session, Child

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


def payment_button(payment_url: str):
    keyboard = InlineKeyboardMarkup()

    keyboard.add(InlineKeyboardButton("ОПЛАТИТЬ БИЛЕТ", url=payment_url))

    return keyboard


def send_payment_info(user: User, child: Child):
    from app.web.init_payment import init

    db = Session()
    try:
        reg: Registration = (
            db.query(Registration).filter(Registration.child_id == child.id).first()
        )

        payment_url = init(
            order_id=int(reg.ticket_code),
            user_id=user.telegram_id,
            phone=user.phone,
            email=user.email,
        )

        if payment_url == "Error":
            bot.send_message(
                user.telegram_id,
                f"Возникла проблема с получением ссылки на оплату\n\n Свяжитесь, пожалуйста, c администратором - @yuknww",
            )

        text = (
            f"Чтобы завершить регистрацию оплатите билет по кнопке ниже\n\n"
            f"Если возникла проблема с оплатой, обратитесь к администратору - @yuknww\n\n"
            f"❗️Также обращаем внимание, что срок действия ссылки на оплату - *24 часа*\n"
            f"Если вы не успели оплатить за это время, пожалуйста, пройдите регистрацию заново\n"
        )

        bot.send_message(
            user.telegram_id,
            text,
            parse_mode="Markdown",
            reply_markup=payment_button(payment_url),
        )
        reg.payment_status = "waiting_payment"
        logger.info(
            f"user_id: {user.telegram_id} отправлена информация об оплате, бот ожидает оплату"
        )
    except Exception as err:
        logger.error(f"Send payment info error: {err}")
        bot.send_message(
            user.telegram_id, "Возникла ошибка, свяжитесь с администратором @yuknww"
        )
    finally:
        db.close()
