import os
from datetime import datetime

from telebot import types
from telebot.types import Message

from app.bot.keyboards.menu_keyboard import menu
from app.bot.keyboards.program_keyboard import gen_program_keyboard
from app.bot.middlewares.logger import logger
from app.db.crud import (
    get_user_by_telegram_id,
    create_user,
    update_user_state,
)
from app.loader import bot
from app.db.models import Session, User, Program

TICKETS_FOLDER = "tickets"  # папка с билетами в корне


@bot.message_handler(commands=["start"])
def start(message: Message):
    text = "Привет, это бот для покупки билета на Масленицу.\n\n" "Выбери действия 👇"
    db = Session()
    try:
        logger.info(
            f"Command start: {message.from_user.first_name} / {message.from_user.id}"
        )
        user = get_user_by_telegram_id(db=db, telegram_id=message.from_user.id)
        markup = menu()
        if user:
            bot.send_message(
                message.chat.id, text, reply_markup=markup, parse_mode="Markdown"
            )
            update_user_state(db=db, state="start", telegram_id=message.from_user.id)
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
        db.rollback()
    finally:
        db.close()


@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu(call: types.CallbackQuery):
    text = (
        "Привет, это бот для покупки билета на Новогодние представления в Шоколадной Фабрике Дедушки Мороза.\n\n"
        "Выбери действия 👇"
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text=text,
        parse_mode="Markdown",
        reply_markup=menu(),
    )


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
        logger.info(f"User press my tickets: {telegram_id}")
        if not user:
            bot.answer_callback_query(callback_query.id, "Вы не зарегистрированы.")
            return

        messages = []
        for child in user.children:
            for reg in child.registrations:
                # показываем только завершённые платежи
                if reg.payment_status != "completed":
                    continue

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
        logger.info(f"User send info about registered child: {telegram_id}")
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


@bot.callback_query_handler(func=lambda c: c.data == "buy_ticket")
def buy_ticket(callback: types.CallbackQuery):
    text = "Выбери программу 👇"
    markup = gen_program_keyboard()

    bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=text,
        reply_markup=markup,
    )
    bot.answer_callback_query(callback.id)


@bot.callback_query_handler(func=lambda c: c.data == "about_program")
def about_program(callback: types.CallbackQuery):
    db = Session()
    try:
        # Получаем список программ из таблицы programs
        programs = db.query(Program).all()

        markup = types.InlineKeyboardMarkup()

        # Создаем кнопку для каждой программы
        for program in programs:
            markup.add(
                types.InlineKeyboardButton(
                    program.name, callback_data=f"show_about_{program.id}"
                )
            )
        markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
        bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text="Выбери программу:",
            reply_markup=markup,
        )
    finally:
        db.close()


@bot.callback_query_handler(func=lambda c: c.data.startswith("show_about_"))
def show_about(callback: types.CallbackQuery):
    program_id = int(callback.data.split("_")[2])  # достаём ID программы
    db = Session()

    try:
        program = db.query(Program).filter_by(id=program_id).first()

        if not program:
            bot.answer_callback_query(
                callback.id, "Программа не найдена.", show_alert=True
            )
            return

        # Описание программы
        description = program.description or "Описание пока недоступно."
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Назад", callback_data="about_program"))
        bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=f"📘 *О программе:*\n\n{description}",
            parse_mode="Markdown",
            reply_markup=markup,
        )

        bot.answer_callback_query(callback.id)

    except Exception as e:
        logger.error(f"Ошибка в show_about: {e}")
        bot.answer_callback_query(callback.id, "Произошла ошибка.", show_alert=True)
        db.rollback()

    finally:
        db.close()
