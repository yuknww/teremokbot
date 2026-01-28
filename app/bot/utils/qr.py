import os
import qrcode
from PIL import Image, ImageDraw
from app.bot.middlewares.logger import logger


def qrcodegen(unique_code):
    qr_url = f"https://t.me/mcscheckregistration_bot?start={unique_code}"

    # Создание QR-кода
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.resize((390, 390))

    # Шаблон билета (относительно этого файла)
    template_path = os.path.join(
        os.path.dirname(__file__), "path_to_ticket_template.png"
    )
    ticket = Image.open(template_path)

    # Вставка QR-кода на шаблон
    ticket.paste(qr_img, (450, 350))

    # Папка tickets в корне проекта
    tickets_dir = os.path.join(os.getcwd(), "tickets")
    os.makedirs(tickets_dir, exist_ok=True)

    # Сохраняем билет
    output_path = os.path.join(tickets_dir, f"{unique_code}.png")
    ticket.save(output_path)
    logger.info(f"Создан и сохранен билет uuid {unique_code}")

    return output_path  # возвращаем путь к файлу