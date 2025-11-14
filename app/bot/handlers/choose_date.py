from psycopg2.errors import UniqueViolation

from app.bot.handlers.reg_children import show_children_for_registration
from app.bot.handlers.start import gen_program_keyboard
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
        db.commit()
        logger.error(f"Ошибка при добавлении program_id")
        bot.send_message(call.message.chat.id, "Возникла ошибка, попробуйте ещё раз")
        # Запрашиваем даты для программы
        dates = db.query(DateSlot).filter(DateSlot.program_id == program_id).all()

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

        # Создаем inline-кнопки для доступных дат
        markup = types.InlineKeyboardMarkup()
        for date in available_dates:
            # Объединяем дату и время из разных колонок
            display_text = (
                f"{date.date.strftime('%d.%m.%Y')} {date.time.strftime('%H:%M')}"
            )
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
    except Exception as e:
        logger.error(f"Возникла ошибка в возврате дат")
        db.rollback()
    finally:
        db.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("date_"))
def choose_date(call: types.CallbackQuery):
    db = Session()
    bot.answer_callback_query(callback_query_id=call.id)
    try:
        date_id = int(call.data.split("_")[1])
        user = get_user_by_telegram_id(db, call.from_user.id)
        user.data = {**(user.data or {}), "date_id": date_id}
        db.commit()
        data = check_phone_and_name(db, call.from_user.id)
        if data["name"] != "OK":
            bot.send_message(call.message.chat.id, "Введите Ваше Имя и Фамилию")
            update_user_state(db=db, telegram_id=call.from_user.id, state="parent_name")
        else:
            show_children_for_registration(call.message.chat.id, call.from_user.id)
    except Exception as e:
        logger.error(f"Возникла ошибка choose date")
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

        bot.send_message(message.chat.id, "Введите ваш номер телефона:")
        update_user_state(db=db, telegram_id=message.from_user.id, state="parent_phone")
    except Exception as e:
        logger.error(f"Возникла ошибка parent name")
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
            bot.send_message(
                message.chat.id,
                "Произошла ошибка, попробуйте ещё раз или свяжитесь с администратором @yuknww",
            )
        update_user_state(db=db, telegram_id=message.from_user.id, state="parent_email")
        bot.send_message(
            message.chat.id, "Укажите адрес электронной почти для отправки чека:"
        )
    except Exception as e:
        logger.error(f"Error parent phone")
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
            except EmailNotValidError as e:
                bot.send_message(
                    message.chat.id,
                    f"❌ Неверный email:\nПожалуйста, попробуйте ещё раз.",
                )
                return

            user = get_user_by_telegram_id(db, telegram_id=user_id)
            user.email = email
            db.commit()
            logger.info(
                f"user_id: {user_id}/{message.from_user.username} указал email {email}"
            )
            show_children_for_registration(message.chat.id, message.from_user.id)
        except Exception as e:
            logger.error(
                f"Возникла ошибка при email. Ошибка {e}, Данные:\n user_id: {user_id}/{message.from_user.username}\n data: {message.text}"
            )
    finally:
        db.close()


@bot.callback_query_handler(func=lambda call: call.data == "menu")
def menu_callback(call: types.CallbackQuery):
    text = """
    *Шоколадная Фабрика Дедушки Мороза*

    Новогодние программы для детей и подростков:
    — Квест «Тайна Шоколадной Фабрики» (5–8 лет)
    — Вечеринка «БезШубы» (от 9 лет)

    📅 Даты проведения: *с 19 декабря по 7 января*
    💰 Стоимость билета: *1 700 руб./ребенок*
    📍 Адрес: г. Вязьма, Красноармейское шоссе, 9, 3 этаж

    💳 Оплата производится онлайн при покупке билета.

    Билет дает право участия в выбранной программе в указанный день.

    ❗ После покупки *билет не подлежит возврату*"""

    markup = gen_program_keyboard()

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=markup,
        parse_mode="Markdown",
    )
