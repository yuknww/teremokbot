from telebot import types


def menu():
    menu_keyboard = types.InlineKeyboardMarkup(row_width=1)

    menu_keyboard.add(
        types.InlineKeyboardButton("Купить билет", callback_data="buy_ticket"),
        types.InlineKeyboardButton("❓О программах", callback_data="about_program"),
        types.InlineKeyboardButton("🎟 Мои билеты", callback_data="my_tickets"),
    )

    return menu_keyboard
