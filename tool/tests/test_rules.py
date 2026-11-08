from dupes.rules import analyse, build_groups, key_values, norm_barcode, norm_name, suggest


def rec(id, **kw):
    base = dict(id=id, name=None, dwh=None, st="Витрина", ph=0, mfr=None, mult=1, dose=None,
                bc=None, mor=None, opt=None, badm=None, date="2024-01-01 00:00:00")
    base.update(kw)
    return base


def test_norm_name_homoglyphs_inside_cyrillic_word():
    assert norm_name("Прокладки uигиенические ТОТАL") == norm_name("прокладки uигиенические тотаl")
    assert norm_name("Сeрум") == norm_name("Серум")  # латинская e внутри кириллицы


def test_norm_name_keeps_latin_words():
    assert norm_name("Vichy Liftactiv") == "vichy liftactiv"


def test_norm_name_punctuation_pieces_and_yo():
    assert norm_name("Ёлка (шт.) №34, 0,5 л") == "елка 34 0 5 л"
    assert norm_name("Масло  кунжутное 100 мл") == norm_name("масло кунжутное 100 мл")


def test_norm_name_keeps_sign_before_digit():
    assert norm_name("Линзы Praktis +3.00") != norm_name("Линзы Praktis -3.00")
    assert norm_name("Хаир-Нейлс") == norm_name("Хаир Нейлс")
    assert norm_name("Спрей SPF50+ 200 мл") != norm_name("Спрей SPF50 200 мл")


def test_norm_barcode():
    assert norm_barcode("4820022240125.5") == "4820022240125"
    assert norm_barcode("382900930015") == "0382900930015"
    assert norm_barcode("4820000131193") == "4820000131193"
    assert norm_barcode("ABC") == "ABC"


def test_key_values_split_and_dedup():
    r = rec(1, mor="112658, 48428,112658", bc="382900930015,0382900930015")
    assert key_values(r, "mor") == ["112658", "48428"]
    assert key_values(r, "bc") == ["0382900930015"]


def test_groups_chain_within_key_and_skip_archive_and_all_in_stock():
    rs = [rec(1, bc="111", ph=5), rec(2, bc="111,222", ph=0), rec(3, bc="222", ph=3),
          rec(4, bc="333", ph=1), rec(5, bc="333", ph=2),           # все в наличии -> нет группы
          rec(6, bc="444", ph=0), rec(7, bc="444", st="Архив")]     # архив не берём
    gs = build_groups(rs, "bc")
    assert [g["items"] for g in gs] == [[1, 2, 3]]
    assert gs[0]["gid"] == "bc:1"
    assert gs[0]["shared"] == ["111", "222"]


def test_suggest_vendor_only_for_name_keys():
    rs = [rec(1, name="Х", mfr="Виола", ph=3, bc="9"), rec(2, name="х", mfr="Лектравы", bc="9")]
    by_id = {r["id"]: r for r in rs}
    g = build_groups(rs, "name")[0]
    assert suggest(g, by_id) == {1: ("vend", "maker"), 2: ("vend", "maker")}
    g = build_groups(rs, "bc")[0]
    assert suggest(g, by_id) == {1: ("orig", "best"), 2: ("dup", "dup")}


def test_unknown_maker_is_not_a_different_maker():
    rs = [rec(1, name="Х", mfr="Агрофарм", ph=3), rec(2, name="х", mfr="Производитель До Уточнения")]
    by_id = {r["id"]: r for r in rs}
    assert suggest(build_groups(rs, "name")[0], by_id)[1] == ("orig", "best")


def test_original_rank_follows_task_order():
    rs = [rec(1, name="Х", mult=1, dose="5 мг", dwh="Х", ph=900),
          rec(2, name="Х", mult=3),                                  # больше кратность — по ТЗ первая
          rec(3, name="Х", mult=3, dose="5 мг")]                     # и дозировка заполнена
    by_id = {r["id"]: r for r in rs}
    s = suggest(build_groups(rs, "name")[0], by_id)
    assert s[3] == ("orig", "best") and s[1] == s[2] == ("dup", "dup")


def test_analyse_covers_all_keys():
    rs = [rec(1, name="А", dwh="А", bc="1", mor="1", opt="1", badm="1", ph=1),
          rec(2, name="а", dwh="а", bc="1", mor="1", opt="1", badm="1")]
    assert [g["key"] for g in analyse(rs)] == ["name", "dwh", "bc", "mor", "opt", "badm"]
