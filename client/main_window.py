from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QInputDialog, QLabel, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QTableWidget, QVBoxLayout, QWidget,
)

from client.api_client import ApiClient, ApiError
from client.dialogs import AddRowDialog, CreateTableDialog, JoinDialog, fill_table_widget, show_error


class MainWindow(QMainWindow):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self.types = api.get_types()
        self.hints = {t["name"]: t["hint"] for t in self.types}
        self.current_table = None  # дані відкритої таблиці, отримані з сервера
        self.loading = False       # True, поки сітка заповнюється (щоб не сприймати це як редагування)

        self.setWindowTitle(f"TableDB – сервер {api.base_url}")
        self.resize(1000, 600)

        # ---------- ліва панель: бази і таблиці ----------
        self.db_combo = QComboBox()
        self.db_combo.currentTextChanged.connect(lambda _: self.refresh_tables())
        new_db_button = QPushButton("Нова база")
        new_db_button.clicked.connect(self.create_database)
        refresh_button = QPushButton("Оновити")
        refresh_button.clicked.connect(lambda: self.refresh_databases(select=self.current_db()))
        self.save_button = QPushButton("Зберегти на диск")
        self.save_button.clicked.connect(self.save_database)
        self.load_button = QPushButton("Завантажити з диска")
        self.load_button.clicked.connect(self.load_database)

        self.tables_list = QListWidget()
        self.tables_list.currentTextChanged.connect(lambda _: self.load_table())
        self.create_table_button = QPushButton("Створити таблицю")
        self.create_table_button.clicked.connect(self.create_table)
        self.drop_table_button = QPushButton("Видалити таблицю")
        self.drop_table_button.clicked.connect(self.drop_table)
        self.join_button = QPushButton("Сполучити таблиці")
        self.join_button.clicked.connect(self.open_join)

        left = QVBoxLayout()
        left.addWidget(QLabel("База даних:"))
        left.addWidget(self.db_combo)
        left.addWidget(new_db_button)
        left.addWidget(refresh_button)
        left.addWidget(self.save_button)
        left.addWidget(self.load_button)
        left.addSpacing(15)
        left.addWidget(QLabel("Таблиці:"))
        left.addWidget(self.tables_list)
        left.addWidget(self.create_table_button)
        left.addWidget(self.drop_table_button)
        left.addWidget(self.join_button)

        # ---------- права панель: вміст таблиці ----------
        self.table_title = QLabel("Таблицю не обрано")
        self.table_widget = QTableWidget()
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.itemChanged.connect(self.on_cell_changed)
        self.add_row_button = QPushButton("Додати рядок")
        self.add_row_button.clicked.connect(self.add_row)
        self.delete_row_button = QPushButton("Видалити рядок")
        self.delete_row_button.clicked.connect(self.delete_row)

        row_buttons = QHBoxLayout()
        row_buttons.addWidget(self.add_row_button)
        row_buttons.addWidget(self.delete_row_button)
        row_buttons.addStretch()

        right = QVBoxLayout()
        right.addWidget(self.table_title)
        right.addWidget(self.table_widget)
        right.addLayout(row_buttons)

        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.addLayout(left, 1)
        main_layout.addLayout(right, 3)
        self.setCentralWidget(central)

        self.refresh_databases()

    # ---------- допоміжне ----------

    def current_db(self):
        return self.db_combo.currentText() or None

    def current_table_name(self):
        item = self.tables_list.currentItem()
        return item.text() if item else None

    def update_buttons(self):
        has_db = self.current_db() is not None
        has_table = self.current_table is not None
        for button in (self.save_button, self.load_button, self.create_table_button):
            button.setEnabled(has_db)
        for button in (self.drop_table_button, self.add_row_button, self.delete_row_button):
            button.setEnabled(has_table)
        self.join_button.setEnabled(has_db and self.tables_list.count() >= 2)

    # ---------- оновлення даних з сервера ----------

    def refresh_databases(self, select=None):
        try:
            names = self.api.list_databases()
        except ApiError as error:
            show_error(self, error)
            names = []
        self.db_combo.blockSignals(True)
        self.db_combo.clear()
        self.db_combo.addItems(names)
        if select in names:
            self.db_combo.setCurrentText(select)
        self.db_combo.blockSignals(False)
        self.refresh_tables()

    def refresh_tables(self, select=None):
        db = self.current_db()
        names = []
        if db:
            try:
                names = self.api.list_tables(db)
            except ApiError as error:
                show_error(self, error)
        self.tables_list.blockSignals(True)
        self.tables_list.clear()
        self.tables_list.addItems(names)
        if names:
            self.tables_list.setCurrentRow(names.index(select) if select in names else 0)
        self.tables_list.blockSignals(False)
        self.load_table()

    def load_table(self):
        db, name = self.current_db(), self.current_table_name()
        self.current_table = None
        if db and name:
            try:
                self.current_table = self.api.get_table(db, name)
            except ApiError as error:
                show_error(self, error)

        self.loading = True
        if self.current_table:
            fill_table_widget(self.table_widget, self.current_table)
            self.table_title.setText(f"Таблиця: {name}")
        else:
            self.table_widget.clear()
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            self.table_title.setText("Таблицю не обрано")
        self.loading = False
        self.update_buttons()

    # ---------- бази ----------

    def create_database(self):
        name, ok = QInputDialog.getText(self, "Нова база", "Назва бази:")
        if not ok:
            return
        try:
            self.api.create_database(name)
        except ApiError as error:
            show_error(self, error)
            return
        self.refresh_databases(select=name.strip())

    def save_database(self):
        try:
            answer = self.api.save_database(self.current_db())
        except ApiError as error:
            show_error(self, error)
            return
        self.statusBar().showMessage(answer["detail"], 5000)

    def load_database(self):
        answer = QMessageBox.question(self, "Завантажити з диска", "Незбережені зміни буде втрачено. Продовжити?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.api.load_database(self.current_db())
        except ApiError as error:
            show_error(self, error)
            return
        self.refresh_tables(select=self.current_table_name())
        self.statusBar().showMessage(result["detail"], 5000)

    # ---------- таблиці ----------

    def create_table(self):
        db = self.current_db()
        dialog = CreateTableDialog(
            self.types, lambda name, columns: self.api.create_table(db, name, columns), self
        )
        if dialog.exec():
            self.refresh_tables(select=dialog.name_edit.text().strip())

    def drop_table(self):
        name = self.current_table_name()
        answer = QMessageBox.question(self, "Видалити таблицю", f"Видалити таблицю '{name}'?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.api.drop_table(self.current_db(), name)
        except ApiError as error:
            show_error(self, error)
            return
        self.refresh_tables()

    def open_join(self):
        try:
            dialog = JoinDialog(self.api, self.current_db(), self)
        except ApiError as error:
            show_error(self, error)
            return
        dialog.exec()
        self.refresh_tables(select=self.current_table_name())  # могла з'явитися нова таблиця

    # ---------- рядки ----------

    def add_row(self):
        db, name = self.current_db(), self.current_table["name"]
        dialog = AddRowDialog(
            self.current_table["columns"], self.hints,
            lambda values: self.api.add_row(db, name, values), self,
        )
        if dialog.exec():
            self.load_table()

    def delete_row(self):
        row = self.table_widget.currentRow()
        if row < 0:
            QMessageBox.information(self, "Видалити рядок", "Спершу оберіть рядок у таблиці")
            return
        try:
            self.api.delete_row(self.current_db(), self.current_table["name"], row)
        except ApiError as error:
            show_error(self, error)
            return
        self.load_table()

    def on_cell_changed(self, item):
        """Редагування прямо в клітинці: весь рядок надсилається на сервер для перевірки."""
        if self.loading or self.current_table is None:
            return
        row = item.row()
        values = [self.table_widget.item(row, c).text() for c in range(self.table_widget.columnCount())]
        try:
            self.api.edit_row(self.current_db(), self.current_table["name"], row, values)
            self.statusBar().showMessage("Рядок змінено (на диск ще не збережено)", 5000)
        except ApiError as error:
            show_error(self, error)
        QTimer.singleShot(0, self.load_table)  # перемалювати з сервера: при помилці повернеться старе значення