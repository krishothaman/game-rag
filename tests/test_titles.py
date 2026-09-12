from game_rag.titles import file_stem, page_url

BASE = "https://sekiro-shadows-die-twice.fandom.com/wiki/"


def test_page_url_replaces_spaces_with_underscores():
    assert page_url("Great Shinobi - Owl") == BASE + "Great_Shinobi_-_Owl"


def test_page_url_keeps_subpage_slash_colon_and_brackets():
    assert page_url("Emma/Dialogue") == BASE + "Emma/Dialogue"
    assert page_url("Ending 1: Shura") == BASE + "Ending_1:_Shura"
    assert page_url("Owl (Father)") == BASE + "Owl_(Father)"


def test_page_url_encodes_unusual_characters():
    assert page_url("Kuro's Charm") == BASE + "Kuro's_Charm"
    assert page_url("Café") == BASE + "Caf%C3%A9"


def test_file_stem_is_readable_and_safe():
    stem = file_stem("Emma/Dialogue")
    assert stem.startswith("Emma_Dialogue-")
    assert len(stem) == len("Emma_Dialogue-") + 8


def test_file_stem_is_unique_and_repeatable():
    assert file_stem("Emma/Dialogue") != file_stem("Emma Dialogue")
    assert file_stem("Owl") == file_stem("Owl")
