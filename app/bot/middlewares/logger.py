import logging
import os

# === Создаём папку logs, если её нет ===
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# === Настройка логгера ===
logger = logging.getLogger("bot_logger")
logger.setLevel(logging.INFO)

# --- Формат логов ---
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# --- Лог в консоль ---
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# --- Лог в файл ---
file_handler = logging.FileHandler(f"{LOG_DIR}/bot.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# === Добавляем обработчики (если их ещё нет) ===
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
