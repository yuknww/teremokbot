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
        logger.info(f"Сформирован QR СБП {response_data["Data"]}")
        return response_data["Data"]
    else:
        logger.error(
            f"Ошибка при инициализации платежа, {response.status_code}/{response.text}"
        )
        return {"Status": "error", "text": response.text}


def init(order_id: int, phone, user_id, email) -> str:
    amount = COST * 100
    description = "Оплата билета на новогоднее мероприятие"

    data = {
        "TerminalKey": TERMINAL_KEY,
        "Amount": amount,
        "OrderId": str(order_id),  # Более явное преобразование в строку
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
                    "PaymentMethod": "full_prepayment",  # Рекомендуемое доп. поле
                    "PaymentObject": "service",  # Рекомендуемое доп. поле
                }
            ],
        },
    }

    response = requests.post(
        url="https://securepay.tinkoff.ru/v2/Init",
        json=data,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        response_data = response.json()
        # payment_url = get_qr(response_data["PaymentId"])
        payment_url = response_data["PaymentURL"]

        logger.info(f"USER_ID: {user_id} Сформирована ссылка на оплату {response_data}")
        logger.info(f"user_id: {user_id} Отправлена ссылка на оплату")
        return payment_url
    else:
        logger.error(
            f"Ошибка при инициализации платежа, {response.status_code}/{response.text}"
        )
        return "Error"
