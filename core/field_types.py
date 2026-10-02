from abc import ABC, abstractmethod
from datetime import datetime, time
from enum import Enum
import math


class FieldType(str, Enum):
    """Перелік типів, які може мати колонка."""
    INTEGER = "integer"
    REAL = "real"
    CHAR = "char"
    STRING = "string"
    TIME = "time"
    TIME_INTERVAL = "timeInvl"


class ValidationError(Exception):
    """Помилка: значення не відповідає типу колонки."""


TIME_FORMAT = "%H:%M:%S"


def parse_time(text: str) -> time:
    """Перетворює рядок 'ГГ:ХХ:СС' на об'єкт time. Якщо формат неправильний – ValueError."""
    return datetime.strptime(text.strip(), TIME_FORMAT).time()


class FieldValue(ABC):
    """Абстрактне значення поля. Кожен підклас сам знає, як себе перевірити."""

    format_hint = ""  # підказка для користувача, який формат очікується

    def __init__(self, raw_value):
        self.raw_value = str(raw_value)  # те, що ввів користувач
        self.value = None                # перетворене значення після validate()

    @abstractmethod
    def validate(self) -> bool:
        """Перевіряє raw_value. Якщо все добре – записує результат у self.value і повертає True."""

    def to_json(self):
        """Як значення зберігається у JSON-файлі."""
        return self.raw_value

    def __eq__(self, other):
        # два значення рівні, якщо вони одного типу і мають однакове значення (потрібно для join)
        return isinstance(other, FieldValue) and type(self) is type(other) and self.value == other.value

    def __hash__(self):
        return hash((type(self), self.value))

    def __str__(self):
        return str(self.to_json())


class IntegerValue(FieldValue):
    format_hint = "ціле число, наприклад 42"

    def validate(self) -> bool:
        try:
            self.value = int(self.raw_value.strip())
            return True
        except ValueError:
            return False

    def to_json(self):
        return self.value


class RealValue(FieldValue):
    format_hint = "дробове число через крапку, наприклад 3.14"

    def validate(self) -> bool:
        try:
            number = float(self.raw_value.strip())
        except ValueError:
            return False
        if not math.isfinite(number):  # відкидаємо nan і inf
            return False
        self.value = number
        return True

    def to_json(self):
        return self.value


class CharValue(FieldValue):
    format_hint = "рівно один символ"

    def validate(self) -> bool:
        if len(self.raw_value) != 1:
            return False
        self.value = self.raw_value
        return True


class StringValue(FieldValue):
    format_hint = "будь-який текст"

    def validate(self) -> bool:
        self.value = self.raw_value
        return True


class TimeValue(FieldValue):
    format_hint = "час у форматі ГГ:ХХ:СС, наприклад 14:30:00"

    def validate(self) -> bool:
        try:
            self.value = parse_time(self.raw_value)
            return True
        except ValueError:
            return False

    def to_json(self):
        return self.value.strftime(TIME_FORMAT)


class TimeIntervalValue(FieldValue):
    format_hint = "інтервал у форматі ГГ:ХХ:СС-ГГ:ХХ:СС, початок не пізніше кінця"

    def validate(self) -> bool:
        parts = self.raw_value.split("-")
        if len(parts) != 2:
            return False
        try:
            start = parse_time(parts[0])
            end = parse_time(parts[1])
        except ValueError:
            return False
        if start > end:
            return False
        self.value = (start, end)
        return True

    @property
    def start_time(self) -> time:
        return self.value[0]

    @property
    def end_time(self) -> time:
        return self.value[1]

    def to_json(self):
        return f"{self.start_time.strftime(TIME_FORMAT)}-{self.end_time.strftime(TIME_FORMAT)}"


# Яким класом обробляється кожен тип
VALUE_CLASSES = {
    FieldType.INTEGER: IntegerValue,
    FieldType.REAL: RealValue,
    FieldType.CHAR: CharValue,
    FieldType.STRING: StringValue,
    FieldType.TIME: TimeValue,
    FieldType.TIME_INTERVAL: TimeIntervalValue,
}


def create_value(field_type: FieldType, raw_value) -> FieldValue:
    """Створює значення потрібного типу і перевіряє його. Якщо значення некоректне – ValidationError."""
    value = VALUE_CLASSES[field_type](raw_value)
    if not value.validate():
        raise ValidationError(
            f"Значення '{raw_value}' не відповідає типу {field_type.value}: очікується {value.format_hint}"
        )
    return value