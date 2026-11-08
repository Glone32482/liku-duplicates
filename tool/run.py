"""Сводка по выгрузке: сколько групп дублей и подсказок по каждому полю.

Запуск из папки tool: ../.venv/bin/python run.py <выгрузка.xlsx>
"""

import sys
from collections import Counter
from pathlib import Path

from dupes.rules import KEYS, analyse
from dupes.sheet import read_export

NAMES = {"name": "Назва товару", "dwh": "Назва DWH", "bc": "Штрих-код", "mor": "Коди Моріон",
         "opt": "Коди Оптима", "badm": "Коди БАДМ"}


def main(path: Path) -> None:
    groups = analyse(read_export(path).records())
    print(f"{'Поле':14} {'груп':>6} {'товарів':>8}  підказки")
    for key in KEYS:
        gs = [g for g in groups if g["key"] == key]
        hints = Counter(s for g in gs for s, _ in g["suggest"].values())
        print(f"{NAMES[key]:14} {len(gs):6} {sum(len(g['items']) for g in gs):8}  {dict(hints)}")
    print(f"{'Усього':14} {len(groups):6} {sum(len(g['items']) for g in groups):8}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
