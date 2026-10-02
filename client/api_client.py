from urllib.parse import quote

import requests


class ApiError(Exception):
    """Помилка від сервера або відсутність зв'язку з ним."""


def part(name: str) -> str:
    """Кодує назву для адреси (щоб українські літери і спецсимволи не ламали URL)."""
    return quote(str(name), safe="")


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, json=None):
        try:
            response = requests.request(method, self.base_url + path, json=json, timeout=10)
        except requests.RequestException:
            raise ApiError(f"Не вдалося підключитися до сервера {self.base_url}")
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            if not isinstance(detail, str):  # помилка формату запиту від FastAPI
                detail = "Некоректний запит"
            raise ApiError(detail)
        return response.json()

    # ---------- типи ----------
    def get_types(self) -> list[dict]:
        return self._request("GET", "/types")

    # ---------- бази ----------
    def list_databases(self) -> list[str]:
        return self._request("GET", "/databases")

    def create_database(self, name: str):
        return self._request("POST", "/databases", {"name": name})

    def save_database(self, db: str):
        return self._request("POST", f"/databases/{part(db)}/save")

    def load_database(self, db: str):
        return self._request("POST", f"/databases/{part(db)}/load")

    # ---------- таблиці ----------
    def list_tables(self, db: str) -> list[str]:
        return self._request("GET", f"/databases/{part(db)}/tables")

    def create_table(self, db: str, name: str, columns: list[dict]):
        return self._request("POST", f"/databases/{part(db)}/tables", {"name": name, "columns": columns})

    def get_table(self, db: str, table: str) -> dict:
        return self._request("GET", f"/databases/{part(db)}/tables/{part(table)}")

    def drop_table(self, db: str, table: str):
        return self._request("DELETE", f"/databases/{part(db)}/tables/{part(table)}")

    # ---------- рядки ----------
    def add_row(self, db: str, table: str, values: list[str]):
        return self._request("POST", f"/databases/{part(db)}/tables/{part(table)}/rows", {"values": values})

    def edit_row(self, db: str, table: str, index: int, values: list[str]):
        return self._request("PUT", f"/databases/{part(db)}/tables/{part(table)}/rows/{index}", {"values": values})

    def delete_row(self, db: str, table: str, index: int):
        return self._request("DELETE", f"/databases/{part(db)}/tables/{part(table)}/rows/{index}")

    # ---------- join ----------
    def join(self, db: str, table1: str, table2: str, field: str, save_as: str | None = None) -> dict:
        body = {"table1": table1, "table2": table2, "field": field, "save_as": save_as}
        return self._request("POST", f"/databases/{part(db)}/join", body)