# TableDB

Часткова реалізація системи управління табличними базами даних.
Варіант 68: додаткові типи `time` і `timeInvl`, додаткова операція – сполучення таблиць за спільним полем (join).

Система складається із сервера (REST API) і двох клієнтів, які працюють з тим самим сервером: десктопного і веб.

## Структура

- `core/` – типи даних, таблиці, валідація, join, збереження у JSON
- `server/` – REST API (FastAPI), видача веб-клієнта
- `client/` – десктоп-клієнт (PySide6)
- `web/` – веб-клієнт (HTML, CSS, JavaScript)
- `tests/` – unit-тести (pytest)
- `data/` – JSON-файли збережених баз

## Запуск

Сервер (потрібен Docker):

    docker compose up --build

- Веб-клієнт: http://127.0.0.1:8000
- Документація API: http://127.0.0.1:8000/docs

Десктоп-клієнт:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python -m client.main

Тести:

    python -m pytest -v