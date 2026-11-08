"""Пишет JSON для tests/parity.mjs: записи выгрузки и группы с подсказками от Python.

Запуск из папки tool: ../.venv/bin/python tests/parity_dump.py <выгрузка.xlsx> <файл.json>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dupes.rules import analyse  # noqa: E402
from dupes.sheet import read_export  # noqa: E402


def main(source: Path, target: Path) -> None:
    records = read_export(source).records()
    target.write_text(json.dumps({"records": records, "groups": analyse(records)}, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
