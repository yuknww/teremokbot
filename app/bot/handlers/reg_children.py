from app.bot.handlers.reg_program import registration_program
from app.bot.middlewares.logger import logger
from app.db.crud import update_user_state, check_user_state, get_user_by_telegram_id
from app.loader import bot
from app.db.models import Session, User, Child
from datetime import datetime
from telebot import types


def show_children_for_registration(
    chat_id: int, telegram_id: int, call: types.CallbackQuery = None
):
    db = Session()

    try:
        # Получаем пользователя по telegram_id
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        date_id = user.data
        markup = types.InlineKeyboardMarkup()

        if user and user.children:
            # Создаем кнопки для каждого ребенка
            logger.info(f"user_id={telegram_id} Show children for_registration (has children)")
            for child in user.children:
                markup.add(
                    types.InlineKeyboardButton(
                        child.child_name, callback_data=f"child_{child.id}"
                    )
                )
            # Кнопка добавить нового ребёнка
            markup.add(
                types.InlineKeyboardButton(
                    "➕ Добавить ребёнка", callback_data="add_child"
                )
            )
            markup.add(
                types.InlineKeyboardButton(
                    "Назад", callback_data=f"program_{date_id["program_id"]}"
                )
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.id,
                text="Выберите ребёнка для регистрации или добавьте нового:",
                reply_markup=markup,
            )
        else:
            # Если детей нет, сразу предлагаем добавить
            markup.add(
                types.InlineKeyboardButton(
                    "➕ Добавить ребёнка", callback_data="add_child"
                )
            )
            bot.send_message(
                chat_id,
                "У вас ещё нет зарегистрированных детей. Добавьте ребёнка для продолжения:",
                reply_markup=markup,
            )
            logger.info(f"user_id={telegram_id} Show children for_registration")
    except Exception as ex:
        logger.error(f"user_id={telegram_id} Возникла ошибка show_children_for_registration: {ex}")
        db.rollback()
    finally:
        db.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("child_"))
def choose_child(call: types.CallbackQuery):
    db = Session()
    try:
        child_id = int(call.data.split("_")[1])
        user = get_user_by_telegram_id(db, call.from_user.id)
        child = db.query(Child).filter(Child.id == child_id).first()

        try:
            registration_program(user, child)
        except Exception:
            bot.send_message(
                call.message.chat.id, "Этот ребёнок уже зарегистрирован на эту дату."
            )
        logger.info(f"user_id={call.from_user.id} Show children for user (choose_child)")
    except Exception as ex:
        logger.error(f"user_id={call.from_user.id} Something error choose child: {ex}")
        db.rollback()
    finally:
        db.close()


@bot.callback_query_handler(func=lambda call: call.data == "add_child")
def add_child(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    db = Session()
    try:
        update_user_state(db, call.from_user.id, "child_name")

        bot.send_message(call.message.chat.id, "Введите Имя и Фамилию ребёнка")
        logger.info(f"user_id={call.from_user.id} Send question about child name")
    finally:
        db.close()


@bot.message_handler(func=lambda message: check_user_state(message, "child_name"))
def child_name(message: types.Message):
    db = Session()
    try:
        name = message.text
        user = get_user_by_telegram_id(db=db, telegram_id=message.from_user.id)
        child = Child(user_id=user.id, child_name=name)
        db.add(child)
        db.commit()
        logger.info(f"user_id={message.from_user.id} Child name {name} added")
        update_user_state(db, message.from_user.id, "child_birth")
        bot.send_message(
            message.chat.id,
            "Укажите дату рождения ребёнка в формате гггг-мм-дд\nНапример: 2010-05-02",
        )
        logger.info(f"user_id={message.from_user.id} Question about birth date")
    except Exception as ex:
        logger.error(f"user_id={message.from_user.id} Something error child_name: {ex}")
        db.rollback()
    finally:
        db.close()


def parse_date(date_str: str):
    """
    Проверяет, что дата соответствует формату гггг-мм-дд.
    Возвращает datetime.date если верно, иначе None
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


@bot.message_handler(func=lambda message: check_user_state(message, "child_birth"))
def child_birth(message: types.Message):
    db = Session()
    try:
        birth_date = parse_date(message.text.strip())

        if not birth_date:
            bot.send_message(
                message.chat.id,
                "Неверный формат даты. Укажите в формате гггг-мм-дд.\nНапример: 2010-05-02",
            )
            return

        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            bot.send_message(message.chat.id, "Пользователь не найден.")
            return

        # Берём последнего ребёнка
        child = (
            db.query(Child)
            .filter(Child.user_id == user.id)
            .order_by(Child.id.desc())
            .first()
        )

        child.birth_date = birth_date
        db.commit()
        logger.info(f"user_id={message.from_user.id} Child birth date")

        registration_program(user, child)
        update_user_state(db, message.from_user.id, "child_reg")

    except Exception as ex:
        logger.error(f"user_id={message.from_user.id} Something error child_birth: {ex}")
        db.rollback()
    finally:
        db.close()
