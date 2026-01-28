from datetime import datetime

from app.bot.handlers.reg_children import show_children_for_registration
from app.bot.keyboards.program_keyboard import gen_program_keyboard
from app.bot.middlewares.logger import logger
from app.db.crud import (
    check_phone_and_name,
    update_user_state,
    get_user_by_telegram_id,
    check_user_state,
    update_user_phone,
    update_user_name,
)
from app.loader import bot
from app.db.models import (
    Session,
    DateSlot,
    Program,
)  # предполагаем, что модель Date есть
from telebot import types
from email_validator import validate_email, EmailNotValidError


@bot.callback_query_handler(func=lambda call: call.data.startswith("program_"))
def return_data_program(call: types.CallbackQuery):
    db = Session()
    try:
        bot.answer_callback_query(callback_query_id=call.id)
        # Получаем ID программы из callback_data
        program_id = int(call.data.split("_")[1])
        user = get_user_by_telegram_id(db=db, telegram_id=call.from_user.id)
        user.data = {**(user.data or {}), "program_id": program_id}
        uid = call.from_user.id
        logger.info(f"user_id={uid} User choose program {program_id}")
        db.commit()
        # Запрашиваем даты для программы
        logger.info(f"user_id={uid} Getting dates")
        dates = db.query(DateSlot).filter(DateSlot.program_id == program_id).all()
        logger.info(f"user_id={uid} Filter dates")
        # Фильтруем только свободные даты
        available_dates = [date for date in dates if date.booked_count < date.capacity]
        menu = types.InlineKeyboardMarkup()
        menu.add(types.InlineKeyboardButton("Назад", callback_data="menu"))
        if not available_dates:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="К сожалению, свободных дат нет 😔",
                reply_markup=menu,
            )
            return
        logger.info(f"user_id={uid} Available dates {available_dates}")
        # Создаем inline-кнопки для доступных дат
        markup = types.InlineKeyboardMarkup()
        logger.info(f"user_id={uid} Parsing dates")
        for date in available_dates:
            dt = datetime.strptime(f"{date.date} {date.time}", "%Y-%m-%d %H:%M")
            display_text = dt.strftime("%d.%m.%Y %H:%M")
            markup.add(
                types.InlineKeyboardButton(
                    display_text, callback_data=f"date_{date.id}"
                )
            )
        markup.add(types.InlineKeyboardButton("Назад", callback_data="menu"))

        program_name = db.query(Program.name).where(Program.id == program_id).scalar()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Вы выбрали: {program_name}\n\nВыберите свободную дату для этой программы:",
            reply_markup=markup,
        )
        logger.info(f"user_id={uid} User sends available date for {program_name}")
    except Exception as e:
        uid = getattr(call, "from_user", None) and getattr(call.from_user, "id", None) or "?"
        logger.error(f"user_id={uid} Возникла ошибка в возврате дат {e} {e.args}")
        db.rollback()
    finally:
        db.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("date_"))
def choose_date(call: types.CallbackQuery):
    db = Session()
    bot.answer_callback_query(callback_query_id=call.id)
    uid = call.from_user.id
    try:
        date_id = int(call.data.split("_")[1])
        date = db.query(DateSlot).get(date_id)
        if date.booked_count >= date.capacity:
            bot.send_message(
                call.message.chat.id, f"Места на выбранную дату закончились"
            )
            return
        user = get_user_by_telegram_id(db, call.from_user.id)
        user.data = {**(user.data or {}), "date_id": date_id}
        db.commit()
        data = check_phone_and_name(db, call.from_user.id)
        if data["name"] != "OK":
            bot.send_message(
                call.message.chat.id, "Введите Ваше Имя и Фамилию (имя взрослого):"
            )
            logger.info(f"user_id={uid} Send question about name")
            update_user_state(db=db, telegram_id=call.from_user.id, state="parent_name")
        else:
            show_children_for_registration(
                call.message.chat.id, call.from_user.id, call
            )
    except Exception as e:
        logger.error(f"user_id={uid} Возникла ошибка choose date {e.args}")
        db.rollback()
    finally:
        db.close()


@bot.message_handler(func=lambda message: check_user_state(message, "parent_name"))
def parent_name(message: types.Message):
    db = Session()
    try:
        name = message.text
        if update_user_name(db=db, telegram_id=message.from_user.id, name=name) is None:
            bot.send_message(
                message.chat.id,
                "Произошла ошибка, попробуйте ещё раз или свяжитесь с администратором @yuknww",
            )
        logger.info(f"user_id={message.from_user.id} User name {name}")
        bot.send_message(message.chat.id, "Введите ваш номер телефона:")
        logger.info(f"user_id={message.from_user.id} Send question about phone")
        update_user_state(db=db, telegram_id=message.from_user.id, state="parent_phone")
    except Exception as e:
        logger.error(f"user_id={message.from_user.id} Возникла ошибка parent name {e.args}")
        db.rollback()
    finally:
        db.close()


@bot.message_handler(func=lambda message: check_user_state(message, "parent_phone"))
def parent_phone(message: types.Message):
    db = Session()
    try:
        phone = message.text
        if (
            update_user_phone(db=db, telegram_id=message.from_user.id, phone=phone)
            is None
        ):
            logger.info(f"user_id={message.from_user.id} User phone {phone}")
            bot.send_message(
                message.chat.id,
                "Произошла ошибка, попробуйте ещё раз или свяжитесь с администратором @yuknww",
            )
        update_user_state(db=db, telegram_id=message.from_user.id, state="parent_email")
        bot.send_message(
            message.chat.id, "Укажите адрес электронной почты для отправки чека:"
        )
        logger.info(f"user_id={message.from_user.id} Send question about email")
    except Exception as e:
        logger.error(f"user_id={message.from_user.id} Error parent phone {e.args}")
        db.rollback()
    finally:
        db.close()


@bot.message_handler(func=lambda m: check_user_state(m, "parent_email"))
def handle_email(message: types.Message):
    db = Session()
    try:
        user_id = message.from_user.id
        user_email = message.text
        try:
            try:
                valid = validate_email(user_email)
                email = valid.normalized
            except EmailNotValidError:
                bot.send_message(
                    message.chat.id,
                    f"❌ Неверный email:\nПожалуйста, попробуйте ещё раз.",
                )
                return

            user = get_user_by_telegram_id(db, telegram_id=user_id)
            user.email = email
            db.commit()
            logger.info(
                f"user_id={user_id} указал email {email}"
            )
            show_children_for_registration(message.chat.id, message.from_user.id)
        except Exception as e:
            logger.error(
                f"user_id={user_id} Возникла ошибка при email: {e}, data={message.text}"
            )
            db.rollback()
    finally:
        db.close()


@bot.callback_query_handler(func=lambda call: call.data == "menu")
def choose_program(call: types.CallbackQuery):
    logger.info(f"user_id={call.from_user.id} choose_program (menu)")
    text = "Выбери программу 👇"
    markup = gen_program_keyboard(telegram_id=call.from_user.id)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=markup,
        parse_mode="Markdown",
    )
