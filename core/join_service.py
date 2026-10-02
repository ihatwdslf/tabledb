from .field_types import ValidationError
from .models import Column, Row, Table


class JoinService:
    """Сполучення (join) двох таблиць за спільним полем."""

    def check_field_compatibility(self, t1: Table, t2: Table, field: str):
        """Перевіряє, що поле є в обох таблицях і має однаковий тип."""
        column1 = t1.get_column(field)  # якщо колонки немає – NotFoundError
        column2 = t2.get_column(field)
        if column1.type != column2.type:
            raise ValidationError(
                f"Типи поля '{field}' несумісні: {column1.type.value} у '{t1.name}' "
                f"і {column2.type.value} у '{t2.name}'"
            )

    def _result_columns(self, t1: Table, t2: Table, field: str) -> list[Column]:
        """Колонки результату: усі колонки Т1, потім колонки Т2 без спільного поля.
        Якщо назви колонок збігаються, до них додається назва таблиці."""
        names1 = {column.name for column in t1.columns}
        names2 = {column.name for column in t2.columns}
        columns = []
        for column in t1.columns:
            name = column.name
            if name != field and name in names2:
                name = f"{t1.name}.{name}"
            columns.append(Column(name, column.type))
        for column in t2.columns:
            if column.name == field:
                continue  # спільне поле вже є з Т1
            name = column.name
            if name in names1:
                name = f"{t2.name}.{name}"
            columns.append(Column(name, column.type))
        return columns

    def execute_join(self, t1: Table, t2: Table, field: str) -> Table:
        if t1.name == t2.name:
            raise ValidationError("Для сполучення потрібно обрати дві різні таблиці")
        self.check_field_compatibility(t1, t2, field)

        index1 = t1.column_index(field)
        index2 = t2.column_index(field)
        result = Table(f"{t1.name}_join_{t2.name}", self._result_columns(t1, t2, field))

        for row1 in t1.rows:          # зовнішній цикл: рядки Т1
            for row2 in t2.rows:      # внутрішній цикл: для кожного рядка Т1 – усі рядки Т2 з початку
                if row1.values[index1] == row2.values[index2]:  # поля рівні?
                    values2 = [v for i, v in enumerate(row2.values) if i != index2]
                    result.rows.append(Row(row1.values + values2))  # додати рядок до результату
        return result