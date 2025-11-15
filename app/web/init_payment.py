import requests
from app.web.token_generator import gen_token, gen_token_sbp
from app.core.config import TERMINAL_KEY, COST
from app.bot.middlewares.logger import logger


def get_qr(payment_id):
    data = {
        "TerminalKey": TERMINAL_KEY,
        "PaymentId": payment_id,
        "DataType": "PAYLOAD",
        "Token": gen_token_sbp(payment_id),
    }

    response = requests.post(
        url="https://securepay.tinkoff.ru/v2/GetQr",
        json=data,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        response_data = response.json()
        qr_data = response_data.get("Data")
        logger.info(f"Сформирован QR СБП {qr_data}")
        return qr_data
    else:
        logger.error(
            f"Ошибка при формировании QR, {response.status_code}/{response.text}"
        )
        return None


def init(order_id: int, phone, user_id, email) -> str:
    amount = COST * 100
    description = "Оплата билета на новогоднее мероприятие"

    data = {
        "TerminalKey": TERMINAL_KEY,
        "Amount": amount,
        "OrderId": str(order_id),
        "Description": description,
        "Token": gen_token(amount=amount, description=description, order_id=order_id),
        "DATA": {
            "OperationInitiatorType": 0,
            "Phone": phone,
        },
        "Receipt": {
            "Email": email,
            "Phone": phone,
            "Taxation": "usn_income",
            "Items": [
                {
                    "Name": "Оплата регистрации на МКС",
                    "Price": amount,
                    "Quantity": 1,
                    "Amount": amount,
                    "Tax": "none",
                    "PaymentMethod": "full_prepayment",
                    "PaymentObject": "service",
                }
            ],
        },
    }

    try:
        response = requests.post(
            url="https://securepay.tinkoff.ru/v2/Init",
            json=data,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        response_data = response.json()
        payment_id = response_data.get("PaymentId")

        if not payment_id:
            logger.error(
                f"Нет PaymentId в ответе TBank: {response_data}, order_id: {order_id}"
            )
            return "Error"

        payment_url = get_qr(payment_id)
        if not payment_url:
            logger.error(f"Не удалось получить QR для PaymentId={payment_id}")
            return "Error"

        logger.info(f"USER_ID: {user_id} Сформирована ссылка на оплату {response_data}")
        return payment_url

    except requests.RequestException as e:
        logger.error(f"Ошибка при инициализации платежа: {e}")
        return "Error"
