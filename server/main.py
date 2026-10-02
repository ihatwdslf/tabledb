import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.field_types import VALUE_CLASSES, FieldType, ValidationError
from core.join_service import JoinService
from core.models import Column, NotFoundError, check_name
from server.storage import StorageAdapter

app = FastAPI(title="TableDB API")
storage = StorageAdapter(os.getenv("DATA_DIR", "data"))
join_service = JoinService()


# ---------- обробка помилок ----------

@app.exception_handler(ValidationError)
async def handle_validation_error(request: Request, error: ValidationError):
    return JSONResponse(status_code=400, content={"detail": str(error)})


@app.exception_handler(NotFoundError)
async def handle_not_found(request: Request, error: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(error)})


# ---------- формат даних у запитах ----------

class DatabaseCreate(BaseModel):
    name: str


class ColumnSchema(BaseModel):
    name: str
    type: str


class TableCreate(BaseModel):
    name: str
    columns: list[ColumnSchema]


class RowData(BaseModel):
    values: list[str]


class JoinRequest(BaseModel):
    table1: str
    table2: str
    field: str
    save_as: str | None = None  # якщо вказано – результат зберігається як нова таблиця


# ---------- типи ----------

@app.get("/types")
def get_types():
    return [{"name": t.value, "hint": VALUE_CLASSES[t].format_hint} for t in FieldType]


# ---------- бази даних ----------

@app.get("/databases")
def list_databases():
    return storage.list_names()


@app.post("/databases", status_code=201)
def create_database(data: DatabaseCreate):
    db = storage.create(data.name)
    return {"name": db.name}


@app.post("/databases/{db_name}/save")
def save_database(db_name: str):
    storage.save(db_name)
    return {"detail": f"Базу '{db_name}' збережено"}


@app.post("/databases/{db_name}/load")
def load_database(db_name: str):
    storage.load(db_name)
    return {"detail": f"Базу '{db_name}' завантажено з диска"}


# ---------- таблиці ----------

@app.get("/databases/{db_name}/tables")
def list_tables(db_name: str):
    return list(storage.get(db_name).tables)


@app.post("/databases/{db_name}/tables", status_code=201)
def create_table(db_name: str, data: TableCreate):
    columns = [Column(c.name, c.type) for c in data.columns]
    table = storage.get(db_name).create_table(data.name, columns)
    return table.to_dict()


@app.get("/databases/{db_name}/tables/{table_name}")
def get_table(db_name: str, table_name: str):
    return storage.get(db_name).get_table(table_name).to_dict()


@app.delete("/databases/{db_name}/tables/{table_name}")
def drop_table(db_name: str, table_name: str):
    storage.get(db_name).drop_table(table_name)
    return {"detail": f"Таблицю '{table_name}' видалено"}


# ---------- рядки ----------

@app.post("/databases/{db_name}/tables/{table_name}/rows", status_code=201)
def add_row(db_name: str, table_name: str, data: RowData):
    table = storage.get(db_name).get_table(table_name)
    return {"values": table.add_row(data.values).to_list()}


@app.put("/databases/{db_name}/tables/{table_name}/rows/{index}")
def edit_row(db_name: str, table_name: str, index: int, data: RowData):
    table = storage.get(db_name).get_table(table_name)
    return {"values": table.edit_row(index, data.values).to_list()}


@app.delete("/databases/{db_name}/tables/{table_name}/rows/{index}")
def delete_row(db_name: str, table_name: str, index: int):
    storage.get(db_name).get_table(table_name).delete_row(index)
    return {"detail": "Рядок видалено"}


# ---------- join ----------

@app.post("/databases/{db_name}/join")
def join_tables(db_name: str, data: JoinRequest):
    db = storage.get(db_name)
    result = join_service.execute_join(db.get_table(data.table1), db.get_table(data.table2), data.field)
    if data.save_as:
        name = check_name(data.save_as, "таблиці")
        if name in db.tables:
            raise ValidationError(f"Таблиця '{name}' вже існує")
        result.name = name
        db.tables[name] = result
    return result.to_dict()