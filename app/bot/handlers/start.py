import os
from datetime import datetime

from telebot import types
from telebot.types import Message

from app.bot.middlewares.logger import logger
from app.db.crud import (
    get_user_by_telegram_id,
    create_user,
)
from app.loader import bot
from app.db.models import Session, Program, User

TICKETS_FOLDER = "tickets"  # папка с билетами в корне


@bot.message_handler(commands=["start"])
def start(message: Message):
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

    db = Session()
    try:
        logger.info(
            f"Command start: {message.from_user.first_name} / {message.from_user.id}"
        )
        user = get_user_by_telegram_id(db=db, telegram_id=message.from_user.id)
        markup = gen_program_keyboard()
        if user:
            bot.send_message(
                message.chat.id, text, reply_markup=markup, parse_mode="Markdown"
            )
        else:
            bot.send_message(
                message.chat.id, text, reply_markup=markup, parse_mode="Markdown"
            )
            create_user(db=db, telegram_id=message.from_user.id)
            logger.info(
                f"User created: {message.from_user.first_name} / {message.from_user.id}"
            )
    except Exception as e:
        logger.error(f"Error processing START: {str(e)}")
    finally:
        db.close()


def gen_program_keyboard():
    db = Session()
    try:
        # Получаем список программ из таблицы programs
        programs = db.query(Program).all()

        markup = types.InlineKeyboardMarkup()

        # Создаем кнопку для каждой программы
        for program in programs:
            markup.add(
                types.InlineKeyboardButton(
                    program.name, callback_data=f"program_{program.id}"
                )
            )

        # Добавляем кнопку "Мои билеты"
        markup.add(
            types.InlineKeyboardButton("🎟 Мои билеты", callback_data="my_tickets")
        )
        logger.info(f"Created {len(programs)} programs")
        return markup
    finally:
        db.close()


MONTH_NAMES = {
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


def format_date(dt: datetime):
    return f"{dt.day:02d} {MONTH_NAMES[dt.month]}"


@bot.callback_query_handler(func=lambda c: c.data == "my_tickets")
def show_my_tickets(callback_query):
    telegram_id = callback_query.from_user.id
    db = Session()
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        logger.info(f"User press my tickets: {user.telegram_id}")
        if not user:
            bot.answer_callback_query(callback_query.id, "Вы не зарегистрированы.")
            return

        messages = []
        for child in user.children:
            for reg in child.registrations:
                program_name = reg.program.name
                date_str = format_date(reg.date_slot.date)
                time_str = reg.date_slot.time.strftime("%H:%M")
                child_name = child.child_name
                ticket_code = reg.ticket_code

                text = f"Ребёнок: {child_name}\nПрограмма: {program_name}\nДата и время: {date_str}, в {time_str}"
                markup = types.InlineKeyboardMarkup()
                if ticket_code:
                    ticket_path = os.path.join(TICKETS_FOLDER, f"{ticket_code}.png")
                    if os.path.exists(ticket_path):
                        btn = types.InlineKeyboardButton(
                            "Показать билет", callback_data=f"show_ticket_{ticket_code}"
                        )
                        markup.add(btn)
                messages.append((text, markup))

        if not messages:
            bot.answer_callback_query(
                callback_query.id, "У вас нет зарегистрированных билетов."
            )
            return

        for text, markup in messages:
            bot.send_message(telegram_id, text, reply_markup=markup)
        logger.info(f"User send info about reg child: {telegram_id}")
        bot.answer_callback_query(callback_query.id)
    finally:
        db.close()


@bot.callback_query_handler(func=lambda c: c.data.startswith("show_ticket_"))
def show_ticket(callback_query):
    ticket_code = callback_query.data.split("show_ticket_")[1]
    ticket_path = os.path.join(TICKETS_FOLDER, f"{ticket_code}.png")
    if os.path.exists(ticket_path):
        # Если Docker, возможно медленно из-за копирования файлов между контейнером и хостом
        with open(ticket_path, "rb") as f:
            bot.send_photo(callback_query.from_user.id, f)
    else:
        bot.answer_callback_query(callback_query.id, "Билет не найден.")
    logger.info(f"Ticket received: {ticket_path}")
