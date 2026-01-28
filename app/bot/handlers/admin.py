from app.loader import bot
from app.core.config import ADMIN_ID
from app.db.models import DateSlot, Session, Registration
from app.bot.middlewares.logger import logger


@bot.message_handler(func=lambda m: m.text and m.text.lower() == "статистика")
def stats_handler(message):
    telegram_id = message.from_user.id
    logger.info(f"user_id={telegram_id} stats request")

    # Проверка прав администратора
    if telegram_id not in ADMIN_ID:
        bot.send_message(telegram_id, "⛔ У вас нет доступа к статистике.")
        return

    db = Session()
    try:
        dates = db.query(DateSlot).order_by(DateSlot.date, DateSlot.time).all()

        if not dates:
            bot.send_message(telegram_id, "Нет доступных дат.")
            return

        text = "📊 *Статистика продаж билетов*\n\n"

        for ds in dates:
            # Кол-во оплаченных регистраций
            paid_count = (
                db.query(Registration)
                .filter(
                    Registration.date_id == ds.id,
                    Registration.payment_status == "completed",
                )
                .count()
            )

            program_name = ds.program.name
            date_str = ds.date
            time_str = ds.time

            text += (
                f"🎄 *{program_name}*\n"
                f"📅 {date_str} в {time_str}\n"
                f"👥 Оплачено: *{paid_count}*\n\n"
            )

        bot.send_message(telegram_id, text, parse_mode="Markdown")
        logger.info(f"user_id={telegram_id} stats sent")

    finally:
        db.close()
