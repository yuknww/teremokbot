import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.core.config import CHECK_REG_TOKEN, ADMIN_ID
from app.db.models import Registration, Child, Program, DateSlot, Session

bot = telebot.TeleBot(CHECK_REG_TOKEN)


def get_session():
    return Session()


# ---------- /start <ticket_code> ----------
@bot.message_handler(commands=["start"])
def handle_start(message):
    if message.from_user.id not in ADMIN_ID:
        return

    args = message.text.split()
    if len(args) != 2:
        bot.send_message(
            message.chat.id,
            "👋 Используй ссылку вида:\n/start <ticket_code>",
        )
        return

    ticket_code = args[1]
    session = get_session()

    reg = (
        session.query(Registration)
        .join(Child)
        .join(Program)
        .join(DateSlot)
        .filter(Registration.ticket_code == ticket_code)
        .first()
    )

    if not reg:
        bot.send_message(message.chat.id, "❌ Билет не найден")
        session.close()
        return

    child = reg.child
    program = reg.program
    date = reg.date_slot

    text = (
        "🎟 Проверка регистрации\n\n"
        f"👶 Ребёнок: {child.child_name}\n"
        f"🎯 Программа: {program.name}\n"
        f"📅 Дата: {date.date.strftime('%d.%m.%Y')}\n"
        f"⏰ Время: {date.time.strftime('%H:%M')}\n"
        f"💳 Статус: {reg.payment_status}\n"
        f"🔑 Билет: {reg.ticket_code}\n\n"
    )

    if reg.payment_status == "entered":
        text += "⚠️ Уже отмечен на входе"
        bot.send_message(message.chat.id, text)
    else:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(
                "✅ Подтвердить вход",
                callback_data=f"enter:{reg.id}",
            )
        )
        bot.send_message(message.chat.id, text, reply_markup=markup)

    session.close()


# ---------- Подтверждение входа ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith("enter:"))
def handle_enter(call):
    reg_id = int(call.data.split(":")[1])
    session = get_session()

    reg = session.query(Registration).get(reg_id)

    if not reg:
        bot.answer_callback_query(call.id, "❌ Регистрация не найдена")
        session.close()
        return

    if reg.payment_status == "entered":
        bot.answer_callback_query(call.id, "⚠️ Уже отмечен")
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None,
        )
        session.close()
        return

    # --- подтверждаем вход ---
    reg.payment_status = "entered"
    session.commit()

    # --- всего ожидается (confirmed + entered) ---
    total_expected = (
        session.query(Registration)
        .filter(
            Registration.date_id == reg.date_id,
            Registration.payment_status.in_(["confirmed", "entered"]),
        )
        .count()
    )

    # --- уже пришли ---
    entered_count = (
        session.query(Registration)
        .filter(
            Registration.date_id == reg.date_id,
            Registration.payment_status == "entered",
        )
        .count()
    )

    bot.answer_callback_query(call.id, "✅ Вход подтверждён")
    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None,
    )

    bot.send_message(
        call.message.chat.id,
        (
            f"🎉 {reg.child.child_name} успешно отмечен\n\n"
            f"👥 Пришло: {entered_count} из {total_expected}"
        ),
    )

    session.close()



if __name__ == "__main__":
    bot.infinity_polling()
