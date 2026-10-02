import json
import re
from pathlib import Path

from .field_types import FieldType, FieldValue, ValidationError, create_value


class NotFoundError(Exception):
    """Помилка: таблицю, колонку або рядок не знайдено."""


NAME_PATTERN = re.compile(r"[\w\-]+")  # літери (зокрема українські), цифри, _ і -


def check_name(name: str, what: str) -> str:
    """Перевіряє назву бази або таблиці, бо вона стає частиною імені файлу."""
    name = name.strip()
    if not NAME_PATTERN.fullmatch(name):
        raise ValidationError(f"Некоректна назва {what}: '{name}'. Дозволено літери, цифри, _ і -")
    return name


class Column:
    def __init__(self, name: str, field_type):
        name = name.strip()
        if not name:
            raise ValidationError("Назва колонки не може бути порожньою")
        try:
            self.type = FieldType(field_type)
        except ValueError:
            raise ValidationError(f"Невідомий тип колонки: '{field_type}'")
        self.name = name

    def to_dict(self) -> dict:
        return {"name": self.name, "type": self.type.value}

    @classmethod
    def from_dict(cls, data: dict) -> "Column":
        return cls(data["name"], data["type"])


class Row:
    def __init__(self, values: list[FieldValue]):
        self.values = values

    def to_list(self) -> list:
        return [value.to_json() for value in self.values]


class Table:
    def __init__(self, name: str, columns: list[Column]):
        self.name = check_name(name, "таблиці")
        if not columns:
            raise ValidationError("Таблиця має містити хоча б одну колонку")
        names = [column.name for column in columns]
        if len(names) != len(set(names)):
            raise ValidationError("Назви колонок не повинні повторюватись")
        self.columns = columns
        self.rows: list[Row] = []

    def column_index(self, column_name: str) -> int:
        for i, column in enumerate(self.columns):
            if column.name == column_name:
                return i
        raise NotFoundError(f"У таблиці '{self.name}' немає колонки '{column_name}'")

    def get_column(self, column_name: str) -> Column:
        return self.columns[self.column_index(column_name)]

    def _parse_row(self, raw_values: list) -> list[FieldValue]:
        """Перетворює введені значення на FieldValue за типами колонок. При помилці – ValidationError."""
        if len(raw_values) != len(self.columns):
            raise ValidationError(
                f"Кількість значень ({len(raw_values)}) не відповідає кількості колонок ({len(self.columns)})"
            )
        values = []
        for column, raw in zip(self.columns, raw_values):
            try:
                values.append(create_value(column.type, raw))
            except ValidationError as error:
                raise ValidationError(f"Колонка '{column.name}': {error}")
        return values

    def validate_row(self, raw_values: list) -> bool:
        try:
            self._parse_row(raw_values)
            return True
        except ValidationError:
            return False

    def _check_index(self, index: int):
        if not 0 <= index < len(self.rows):
            raise NotFoundError(f"Рядка з номером {index} не існує")

    def add_row(self, raw_values: list) -> Row:
        row = Row(self._parse_row(raw_values))
        self.rows.append(row)
        return row

    def edit_row(self, index: int, raw_values: list) -> Row:
        self._check_index(index)
        row = Row(self._parse_row(raw_values))
        self.rows[index] = row
        return row

    def delete_row(self, index: int):
        self._check_index(index)
        del self.rows[index]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "columns": [column.to_dict() for column in self.columns],
            "rows": [row.to_list() for row in self.rows],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Table":
        table = cls(data["name"], [Column.from_dict(c) for c in data["columns"]])
        for raw_values in data["rows"]:
            table.add_row(raw_values)  # під час зчитування дані знову проходять перевірку
        return table


class Database:
    def __init__(self, name: str):
        self.name = check_name(name, "бази")
        self.tables: dict[str, Table] = {}  # ключ – назва таблиці

    def create_table(self, name: str, columns: list[Column]) -> Table:
        table = Table(name, columns)
        if table.name in self.tables:
            raise ValidationError(f"Таблиця '{table.name}' вже існує")
        self.tables[table.name] = table
        return table

    def drop_table(self, name: str):
        self.get_table(name)  # перевіряємо, що таблиця існує
        del self.tables[name]

    def get_table(self, name: str) -> Table:
        if name not in self.tables:
            raise NotFoundError(f"Таблиці '{name}' не існує")
        return self.tables[name]

    def to_dict(self) -> dict:
        return {"name": self.name, "tables": [t.to_dict() for t in self.tables.values()]}

    @classmethod
    def from_dict(cls, data: dict) -> "Database":
        db = cls(data["name"])
        for table_data in data["tables"]:
            table = Table.from_dict(table_data)
            db.tables[table.name] = table
        return db

    def save(self, path: str):
        text = json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        Path(path).write_text(text, encoding="utf-8")

    def load(self, path: str):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        loaded = Database.from_dict(data)
        self.name = loaded.name
        self.tables = loaded.tables
