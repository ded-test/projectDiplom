FROM python:3.12-slim

WORKDIR /app

# Обновляем списки пакетов и устанавливаем зависимости
RUN apt-get update --fix-missing && \
    apt-get install -y \
    gcc \
    libpq-dev \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY app.py .

# Переменные окружения
ENV PYTHONUNBUFFERED=1

# Запуск приложения
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]