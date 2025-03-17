FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${PATH}:/root/.local/bin"

# Копирование файлов Poetry для установки зависимостей
COPY pyproject.toml poetry.lock* /app/

# Настройка Poetry для создания виртуального окружения в проекте
RUN poetry config virtualenvs.create false

# Установка зависимостей
RUN poetry install --no-interaction --no-ansi --no-root

# Копирование кода приложения
COPY . /app/

# # Создание пользователя с ограниченными правами
# RUN adduser --disabled-password --gecos "" appuser
# USER appuser

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]