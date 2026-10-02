# TableDB

Часткова реалізація системи управління табличними базами даних.
Варіант 68: додаткові типи `time` і `timeInvl`, додаткова операція – сполучення таблиць за спільним полем (join).

## Структура

- `core/` – типи даних, таблиці, валідація, join, збереження у JSON
- `server/` – REST API (FastAPI)
- `client/` – десктоп-клієнт (PySide6)
- `tests/` – unit-тести (pytest)

## Запуск

Сервер (потрібен Docker):

    docker compose up --build

Документація API: http://127.0.0.1:8000/docs

Клієнт:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python -m client.main

Тести:

    python -m pytest -v