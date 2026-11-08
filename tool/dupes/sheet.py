"""Чтение выгрузки товаров DWH. Столбцы ищутся по заголовку в первой строке, порядок не важен."""

from dataclasses import dataclass
from pathlib import Path

import openpyxl

# Столбец выгрузки -> короткое имя поля в правилах. Те же имена в docs/index.html.
FIELDS = {
    "ID эталонного товара": "id",
    "Название товара": "name",
    "Название товара DWH": "dwh",
    "Статус": "st",
    "Аптек": "ph",
    "Производитель": "mfr",
    "Кратность": "mult",
    "Дозировка": "dose",
    "Штрих-код": "bc",
    "Коды Морион": "mor",
    "Коды Оптима": "opt",
    "Коды БАДМ": "badm",
    "Дата создания": "date",
}
REQUIRED = tuple(FIELDS)


class SheetError(ValueError):
    pass


@dataclass(frozen=True)
class Export:
    header: tuple[str, ...]
    rows: list[tuple]

    def records(self) -> list[dict]:
        """Строки как словари с короткими именами полей из FIELDS."""
        at = {short: self.header.index(column) for column, short in FIELDS.items()}
        return [{short: cell(row[i]) for short, i in at.items()} for row in self.rows]


def cell(value):
    """Значение ячейки как его увидит сайт: целое число из float без «.0», строка без пробелов по краям."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def read_export(path: Path) -> Export:
    sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    raw = list(sheet.iter_rows(values_only=True))
    if not raw:
        raise SheetError(f"Файл {path.name} пустой.")
    header = tuple("" if c is None else str(c).strip() for c in raw[0])
    missing = [name for name in REQUIRED if name not in header]
    if missing:
        raise SheetError(f"В файле {path.name} нет столбцов: {', '.join(missing)}.")
    width = len(header)
    rows = [tuple(row[:width]) + (None,) * (width - len(row))
            for row in raw[1:] if any(c not in (None, "") for c in row)]
    return Export(header, rows)
