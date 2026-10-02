from pathlib import Path

from core.field_types import ValidationError
from core.models import Database, NotFoundError, check_name


class StorageAdapter:
    """Зберігає відкриті бази в пам'яті і записує/читає їх у JSON-файли в папці data_dir."""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.databases: dict[str, Database] = {}  # відкриті бази

    def _path(self, name: str) -> Path:
        return self.data_dir / f"{name}.json"

    def list_names(self) -> list[str]:
        """Усі бази: збережені на диску і створені, але ще не збережені."""
        on_disk = {path.stem for path in self.data_dir.glob("*.json")}
        return sorted(on_disk | set(self.databases))

    def create(self, name: str) -> Database:
        name = check_name(name, "бази")
        if name in self.list_names():
            raise ValidationError(f"База '{name}' вже існує")
        db = Database(name)
        self.databases[name] = db
        return db

    def get(self, name: str) -> Database:
        if name in self.databases:
            return self.databases[name]
        if self._path(name).exists():
            return self.load(name)  # база є на диску, але ще не відкрита
        raise NotFoundError(f"Бази '{name}' не існує")

    def save(self, name: str):
        self.get(name).save(self._path(name))

    def load(self, name: str) -> Database:
        path = self._path(name)
        if not path.exists():
            raise NotFoundError(f"База '{name}' ще не збережена на диск")
        db = Database(name)
        db.load(path)
        self.databases[name] = db
        return db