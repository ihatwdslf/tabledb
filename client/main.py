import os
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from client.api_client import ApiClient, ApiError
from client.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    api = ApiClient(os.getenv("TABLEDB_SERVER", "http://127.0.0.1:8000"))
    try:
        window = MainWindow(api)
    except ApiError as error:
        QMessageBox.critical(
            None, "Сервер недоступний",
            f"{error}\n\nПереконайтесь, що сервер запущено (docker compose up)."
        )
        sys.exit(1)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()