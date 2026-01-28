from flask import Blueprint, jsonify, request, abort
from app.core.config import ADMIN_ID, PASSWORD
from app.db.models import User, Registration, Session, Child
from app.db.crud import update_user_state, delete_registration_by_ticket
from app.bot.handlers.success_payment import process_successful_payment
from app.loader import bot
from app.bot.middlewares.logger import logger

web_bp = Blueprint("web", __name__)

# Список разрешённых IP (можно вынести в конфиг)
ALLOWED_NETWORKS = [
    "91.194.226.0/23",
    "91.218.132.0/24",
    "91.218.133.0/24",
    "91.218.134.0/24",
    "91.218.135.0/24",
    "212.49.24.0/24",
    "212.233.80.0/24",
    "212.233.81.0/24",
    "212.233.82.0/24",
    "212.233.83.0/24",
    "91.194.226.181/32",  # Тестовая среда (один IP)
]


def is_ip_allowed(ip):
    """Проверяет, принадлежит ли IP разрешённой подсети."""
    from ipaddress import ip_network, ip_address

    for network in ALLOWED_NETWORKS:
        if ip_address(ip) in ip_network(network, strict=False):
            return True
    return False


@web_bp.before_request
def restrict_by_ip():
    client_ip = request.remote_addr  # Или get_client_ip() из прошлых примеров
    if not is_ip_allowed(client_ip):
        abort(403)


@web_bp.route("/")
def index():
    return "Hello World!"


@web_bp.route("/notify", methods=["POST"])
def handle_callback():
    db = Session()
    try:
        logger.info(f"Callback received from {request.remote_addr}: {request.json}")
        callback_data = request.json

        # 2. Обработка по статусам
        status = callback_data["Status"]
        order_id = callback_data["OrderId"]

        if status == "CONFIRMED":
            logger.info(f"Payment confirmed order_id={order_id}")
            try:
                for admin in ADMIN_ID:
                    bot.send_message(
                        admin,
                        f"✅ Получена оплата\nPaymentId: {callback_data["PaymentId"]}\nOrderID: {order_id}",
                    )
                process_successful_payment(callback_data)
            except Exception as e:
                logger.error(f"Error processing CONFIRMED order_id={order_id}: {str(e)}")
            return "OK", 200

        elif status in ["CANCELED", "REVERSED", "REJECTED"]:
            logger.info(f"Payment canceled order_id={order_id}")
            try:
                reg = db.query(Registration).filter_by(ticket_code=order_id).first()
                user_id = reg.child.user.telegram_id
                logger.info(f"user_id={user_id} Payment canceled, notifying")
                bot.send_message(
                    user_id,
                    "⚠️ Оплата отменена. Пожалуйста, начните регистрацию заново",
                )
                delete_registration_by_ticket(db=db, ticket_code=order_id)
            except Exception as e:
                logger.error(f"Error processing CANCELED order_id={order_id}: {str(e)}")
            return "OK", 200

        elif status == "REFUNDED":
            logger.info(f"Refund processed order_id={order_id}")
            try:
                reg = db.query(Registration).filter_by(ticket_code=order_id).first()
                user_id = reg.child.user.telegram_id
                logger.info(f"user_id={user_id} Refund, notifying")
                text = (
                    f"❌ Регистрация {order_id} отменена.\n\n"
                    "Если вы не отменяли регистрацию, свяжитесь с администратором - @yuknww"
                )
                bot.send_message(user_id, text)
                delete_registration_by_ticket(db=db, ticket_code=order_id)
            except Exception as e:
                logger.error(f"Error processing REFUNDED order_id={order_id}: {str(e)}")
            return "OK", 200

        elif status == "AUTHORIZED":
            logger.info(f"Authorized payment order_id={order_id}")
            return "OK", 200

        else:
            logger.warning(f"Unknown status received: {status}")
            return "OK", 200

    except Exception as e:
        logger.critical(f"Critical error in callback handler: {str(e)}")
        return "SERVER ERROR", 500
    finally:
        db.close()


# if __name__ == "__main__":
#     app.run(host="89.111.143.157", port=5000, debug=False)
