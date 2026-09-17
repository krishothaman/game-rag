import json

from game_rag.chunker import Chunk, chunk_all, chunk_page, page_type
from game_rag.titles import file_stem, page_url


def make_page(title, sections, categories=("Characters",)):
    return {
        "title": title,
        "url": page_url(title),
        "categories": list(categories),
        "sections": [{"heading": h, "level": 2, "text": t} for h, t in sections],
    }


def numbered(n, start=0):
    return " ".join(f"w{i}" for i in range(start, start + n))


def test_long_page_is_cut_into_overlapping_chunks():
    page = make_page("Owl", [("Description", numbered(24))])
    chunks = chunk_page(page, size=10, overlap=3)
    # starts at word 0, 7, 14. the third one already reaches the last word so it stops there
    assert [c.text for c in chunks] == [numbered(10, 0), numbered(10, 7), numbered(10, 14)]


def test_neighbouring_chunks_share_the_overlap():
    page = make_page("Owl", [("Description", numbered(24))])
    first, second = chunk_page(page, size=10, overlap=3)[:2]
    assert first.text.split()[-3:] == second.text.split()[:3]


def test_short_page_is_one_chunk():
    page = make_page("Dying Monk", [("Description", "A monk who is dying.")])
    assert [c.text for c in chunk_page(page, size=10, overlap=3)] == ["A monk who is dying."]


def test_chunks_never_cross_a_section_boundary():
    page = make_page("Owl", [("Description", numbered(5)), ("Location", numbered(8, 5))])
    chunks = chunk_page(page, size=10, overlap=3)
    assert [(c.section, c.text) for c in chunks] == [("Description", numbered(5)), ("Location", numbered(8, 5))]


def test_small_sections_get_packed_together():
    page = make_page("Owl", [("A", numbered(3)), ("B", numbered(4, 3)), ("C", numbered(8, 7))])
    chunks = chunk_page(page, size=10, overlap=3)
    assert [(c.section, c.text) for c in chunks] == [("A", numbered(7)), ("C", numbered(8, 7))]


def test_long_section_after_a_short_one_is_split_on_its_own():
    page = make_page("Owl", [("A", numbered(3)), ("B", numbered(24, 3))])
    chunks = chunk_page(page, size=10, overlap=3)
    assert [c.section for c in chunks] == ["A", "B", "B", "B"]
    assert chunks[1].text == numbered(10, 3)


def test_chunk_labels_and_ids():
    page = make_page("Emma/Dialogue", [("Introduction", numbered(12))], categories=["Dialogues"])
    chunks = chunk_page(page, size=10, overlap=3)
    assert chunks[0] == Chunk(
        id=f"{file_stem('Emma/Dialogue')}-0",
        text=numbered(10),
        page_title="Emma/Dialogue",
        section="Introduction",
        url=page_url("Emma/Dialogue"),
        page_type="character",
        game="Sekiro",
    )
    assert chunks[1].id == f"{file_stem('Emma/Dialogue')}-1"


def test_page_type_picks_the_most_specific_category():
    assert page_type(["Endings"]) == "ending"
    assert page_type(["Bosses", "Enemies", "Characters"]) == "character"
    assert page_type(["Key Items", "Items"]) == "item"
    assert page_type(["Locations"]) == "location"
    assert page_type(["Lore"]) == "lore"
    assert page_type(["Something Else"]) == "lore"


def test_chunk_all_reads_every_clean_page(tmp_path):
    for title in ["Owl", "Emma"]:
        page = make_page(title, [("Description", numbered(5))])
        (tmp_path / f"{file_stem(title)}.json").write_text(json.dumps(page), encoding="utf-8")
    chunks = chunk_all(tmp_path)
    assert sorted(c.page_title for c in chunks) == ["Emma", "Owl"]


def test_embed_text_starts_with_the_page_and_section():
    page = make_page("Ending 2: Immortal Severance", [("Overview", "Wolf gives Kuro the Tears.")],
                     categories=("Endings",))
    chunk = chunk_page(page)[0]
    assert chunk.text == "Wolf gives Kuro the Tears."
    assert chunk.embed_text == "Ending 2: Immortal Severance > Overview\nWolf gives Kuro the Tears."
