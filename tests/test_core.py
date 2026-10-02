import pytest

from core.field_types import FieldType, ValidationError, create_value
from core.join_service import JoinService
from core.models import Column, Database, NotFoundError, Table


# ---------- типи даних ----------

def test_integer_value():
    assert create_value(FieldType.INTEGER, "42").value == 42
    with pytest.raises(ValidationError):
        create_value(FieldType.INTEGER, "abc")
    with pytest.raises(ValidationError):
        create_value(FieldType.INTEGER, "3.5")


def test_char_value():
    assert create_value(FieldType.CHAR, "a").value == "a"
    with pytest.raises(ValidationError):
        create_value(FieldType.CHAR, "ab")


def test_time_interval_value():
    interval = create_value(FieldType.TIME_INTERVAL, "09:00:00-18:00:00")
    assert interval.to_json() == "09:00:00-18:00:00"
    with pytest.raises(ValidationError):
        create_value(FieldType.TIME_INTERVAL, "18:00:00-09:00:00")  # початок пізніше кінця
    with pytest.raises(ValidationError):
        create_value(FieldType.TIME_INTERVAL, "09:00")  # неправильний формат


# ---------- таблиця ----------

def test_table_rejects_invalid_row():
    table = Table("students", [Column("name", FieldType.STRING), Column("age", FieldType.INTEGER)])
    table.add_row(["Олена", "20"])
    with pytest.raises(ValidationError):
        table.add_row(["Максим", "двадцять"])
    assert len(table.rows) == 1  # некоректний рядок не додався


def test_table_rejects_duplicate_columns():
    with pytest.raises(ValidationError):
        Table("t", [Column("a", FieldType.STRING), Column("a", FieldType.INTEGER)])


# ---------- join (індивідуальна операція) ----------

def make_tables():
    students = Table("students", [
        Column("name", FieldType.STRING),
        Column("reg_time", FieldType.TIME),
    ])
    students.add_row(["Олена", "09:15:00"])
    students.add_row(["Максим", "14:30:00"])
    students.add_row(["Ірина", "09:15:00"])

    exams = Table("exams", [
        Column("subject", FieldType.STRING),
        Column("reg_time", FieldType.TIME),
        Column("name", FieldType.STRING),
    ])
    exams.add_row(["Математика", "09:15:00", "Петренко"])
    exams.add_row(["Фізика", "16:00:00", "Коваль"])
    exams.add_row(["Хімія", "14:30:00", "Шевченко"])
    return students, exams


def test_join():
    students, exams = make_tables()
    result = JoinService().execute_join(students, exams, "reg_time")

    assert [column.name for column in result.columns] == [
        "students.name", "reg_time", "subject", "exams.name"
    ]
    assert [row.to_list() for row in result.rows] == [
        ["Олена", "09:15:00", "Математика", "Петренко"],
        ["Максим", "14:30:00", "Хімія", "Шевченко"],
        ["Ірина", "09:15:00", "Математика", "Петренко"],
    ]


def test_join_incompatible_types():
    t1 = Table("a", [Column("x", FieldType.INTEGER)])
    t2 = Table("b", [Column("x", FieldType.STRING)])
    with pytest.raises(ValidationError):
        JoinService().execute_join(t1, t2, "x")


def test_join_missing_field():
    students, exams = make_tables()
    with pytest.raises(NotFoundError):
        JoinService().execute_join(students, exams, "subject")


# ---------- збереження і зчитування ----------

def test_save_and_load(tmp_path):
    db = Database("test_db")
    table = db.create_table("t", [Column("period", FieldType.TIME_INTERVAL)])
    table.add_row(["08:00:00-12:00:00"])

    path = tmp_path / "test_db.json"
    db.save(path)

    loaded = Database("other")
    loaded.load(path)
    assert loaded.name == "test_db"
    assert loaded.get_table("t").rows[0].to_list() == ["08:00:00-12:00:00"]