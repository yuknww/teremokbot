# Используем официальный Python
FROM python:3.13-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем зависимости и проект
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Копируем .env в контейнер
COPY .env .do

# Команда запуска бота
CMD ["python", "main.py"]
