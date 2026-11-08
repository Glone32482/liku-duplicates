"""Поиск групп дублей и подсказки решений. Эталон для блока check в docs/index.html.

Правила: .wiki/decisions/groups-per-key.md и .wiki/decisions/rules.md.
Запись товара — словарь с полями из sheet.FIELDS (id, name, dwh, st, ph, mfr, mult, dose, bc, mor,
opt, badm, date).
"""

import re

KEYS = ("name", "dwh", "bc", "mor", "opt", "badm")
NAME_KEYS = ("name", "dwh")
SKIP_STATUS = "Архив"
UNKNOWN_MAKER = "производитель до уточнения"

# Латинские буквы, похожие на кириллические. Меняются только в словах, где есть обе азбуки.
HOMOGLYPHS = str.maketrans("abcehikmoptxy", "авсенікмортху")
CYR = "а-яёіїєґ"
LAT = "a-z"
WORD = re.compile(rf"[{CYR}{LAT}]+")
MIXED = re.compile(rf"[{CYR}]").search
# «+» всегда значим (SPF50+, формат А+, линзы +3.00). «-» значим только перед цифрой (линзы -3.00).
PUNCT = re.compile(r"[()\[\]\"'«»“”.,;:/\\&*_]|-(?!\d)")
SPACES = re.compile(r"\s+")


def text(value) -> str:
    return "" if value is None else str(value)


def norm_name(value) -> str:
    """Название для сравнения: регистр, ё, латиница внутри кириллических слов, пунктуация, «шт», «№»."""
    s = text(value).lower().replace("ё", "е")

    def fix(m: re.Match) -> str:
        w = m.group()
        return w.translate(HOMOGLYPHS) if MIXED(w) and re.search(rf"[{LAT}]", w) else w

    s = WORD.sub(fix, s)
    s = PUNCT.sub(" ", s).replace("№", " ")
    s = " ".join(t for t in SPACES.split(s) if t and t != "шт")
    return s


BARCODE_TAIL = re.compile(r"^(\d{8,14})\.\d+$")


def norm_barcode(code: str) -> str:
    """Штрих-код: хвост «.5» от Excel отбрасывается, 12 цифр (UPC-A) дополняются нулём до EAN-13."""
    m = BARCODE_TAIL.match(code)
    if m:
        code = m.group(1)
    if len(code) == 12 and code.isdigit():
        code = "0" + code
    return code


def split_codes(value) -> list[str]:
    return [c.strip() for c in text(value).split(",") if c.strip()]


def key_values(record: dict, key: str) -> list[str]:
    """Значения поля для поиска дублей, без повторов, в порядке появления."""
    if key in NAME_KEYS:
        v = norm_name(record.get(key))
        out = [v] if v else []
    elif key == "bc":
        out = [norm_barcode(c) for c in split_codes(record.get(key))]
    else:
        out = split_codes(record.get(key))
    return list(dict.fromkeys(out))


def pharmacies(record: dict) -> int:
    v = record.get("ph")
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def build_groups(records: list[dict], key: str) -> list[dict]:
    """Группы по одному полю. Внутри поля товары склеиваются цепочкой через общие значения.

    Берутся группы из 2+ товаров без статуса «Архив», где хотя бы один товар не в наличии.
    Товары в группе — по возрастанию ID, группы — по возрастанию ID первого товара.
    """
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_id = {}
    for r in records:
        if r.get("st") == SKIP_STATUS:
            continue
        values = key_values(r, key)
        if not values:
            continue
        by_id[r["id"]] = r
        for v in values:
            parent[find(("v", v))] = find(("id", r["id"]))

    buckets: dict = {}
    for rid in by_id:
        buckets.setdefault(find(("id", rid)), []).append(rid)

    groups = []
    for ids in buckets.values():
        if len(ids) < 2:
            continue
        items = sorted(ids)
        if all(pharmacies(by_id[i]) > 0 for i in items):
            continue
        counts: dict = {}
        for i in items:
            for v in key_values(by_id[i], key):
                counts[v] = counts.get(v, 0) + 1
        shared = [v for v, n in counts.items() if n > 1]
        groups.append({"gid": f"{key}:{items[0]}", "key": key, "items": items, "shared": shared})
    groups.sort(key=lambda g: g["items"][0])
    return groups


def maker(record: dict) -> str:
    m = text(record.get("mfr")).strip().lower()
    return "" if m == UNKNOWN_MAKER else m


def rank(record: dict) -> tuple:
    """Порядок выбора «Оригінал»: сначала правила ТЗ (кратность больше, дозировка заполнена),
    затем заполнена «Назва DWH», больше аптек, статус «Витрина», раньше создан, меньше ID."""
    return (
        -(record.get("mult") or 0),
        0 if text(record.get("dose")).strip() else 1,
        0 if text(record.get("dwh")).strip() else 1,
        -pharmacies(record),
        0 if record.get("st") == "Витрина" else 1,
        text(record.get("date")),
        record["id"],
    )


def suggest(group: dict, by_id: dict) -> dict:
    """Подсказка по каждому товару группы: {id: (статус, причина)}.

    Статусы: orig, dup, vend. Причины: maker (разные производители), best (лучший по правилам),
    dup (дубль лучшего). Разные производители дают «Vendor» только для групп по названию:
    одинаковый код у разных производителей — ошибка оцифровки одного из товаров, а не другой товар.
    """
    items = [by_id[i] for i in group["items"]]
    makers = {maker(r) for r in items} - {""}
    if group["key"] in NAME_KEYS and len(makers) > 1:
        return {r["id"]: ("vend", "maker") for r in items}
    best = min(items, key=rank)
    return {r["id"]: ("orig", "best") if r is best else ("dup", "dup") for r in items}


def analyse(records: list[dict]) -> list[dict]:
    """Все группы по всем полям с подсказками."""
    by_id = {r["id"]: r for r in records}
    out = []
    for key in KEYS:
        for g in build_groups(records, key):
            s = suggest(g, by_id)
            out.append({**g, "suggest": {str(i): list(v) for i, v in s.items()}})
    return out
