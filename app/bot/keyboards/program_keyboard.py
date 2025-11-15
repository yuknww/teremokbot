from app.db.models import Session, Program
from telebot import types
from app.bot.middlewares.logger import logger


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
        markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
        logger.info(f"Created {len(programs)} programs")
        return markup
    finally:
        db.close()
