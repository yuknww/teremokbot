from telebot import types
from telebot.types import Message
from app.db.crud import (
    get_user_by_telegram_id,
    update_user_state,
    create_user,
    check_user_state,
    update_user_name,
    update_user_phone,
)
from app.loader import bot
from app.db.models import Session


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
    user = get_user_by_telegram_id(db=db, telegram_id=message.from_user.id)

    if user:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "➕ Зарегистрировать ребёнка", callback_data="register_child"
            ),
            types.InlineKeyboardButton("🎟 Мои билеты", callback_data="my_tickets"),
        )
        bot.send_message(
            message.chat.id, text, reply_markup=markup, parse_mode="Markdown"
        )
    else:
        bot.send_message(
            message.chat.id,
            "Добрый день, это бот от Шоколадной Фабрики Деда Мороза\n"
            "Перед началом, введите пожалуйста ваше имя:",
        )
        create_user(db=db, telegram_id=message.from_user.id)
        update_user_state(db=db, telegram_id=message.from_user.id, state="parent_name")


@bot.message_handler(func=lambda message: check_user_state(message, "parent_name"))
def parent_name(message: Message):
    db = Session()
    name = message.text
    if update_user_name(db=db, telegram_id=message.from_user.id, name=name) is None:
        bot.send_message(
            message.chat.id,
            "Произошла ошибка, попробуйте ещё раз или свяжитесь с администратором @yuknww",
        )

    bot.send_message(message.chat.id, "Введите ваш номер телефона:")
    update_user_state(db=db, telegram_id=message.from_user.id, state="parent_phone")


@bot.message_handler(func=lambda message: check_user_state(message, "parent_phone"))
def parent_phone(message: Message):
    db = Session()
    phone = message.text
    if update_user_phone(db=db, telegram_id=message.from_user.id, phone=phone) is None:
        bot.send_message(
            message.chat.id,
            "Произошла ошибка, попробуйте ещё раз или свяжитесь с администратором @yuknww",
        )
    bot.send_message(message.chat.id, "Спасибо, ниже вы можете выбрать утренник и дату")
    start(message)
    update_user_state(db=db, telegram_id=message.from_user.id, state="start")
