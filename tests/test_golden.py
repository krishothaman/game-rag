from game_rag.chunker import Chunk
from game_rag.golden import load_golden, pages_found
from game_rag.library import Hit


def hit(title):
    return Hit(chunk=Chunk(id=title, text="...", page_title=title, section="Overview",
                           url="https://example.com", page_type="lore"), distance=0.3)


def test_load_golden_reads_one_question_per_line_and_skips_blanks(tmp_path):
    path = tmp_path / "golden.jsonl"
    path.write_text(
        '{"id": 1, "question": "Who is Emma?", "facts": ["a doctor"], "pages": ["Emma"]}\n\n'
        '{"id": 2, "question": "Is Radahn in Sekiro?", "facts": [], "pages": [], "not_covered": true}\n',
        encoding="utf-8",
    )
    items = load_golden(path)
    assert [q.id for q in items] == [1, 2]
    assert items[0].pages == ["Emma"]
    assert not items[0].not_covered
    assert items[1].not_covered


def test_pages_found_only_counts_expected_pages_in_the_hits(tmp_path):
    path = tmp_path / "golden.jsonl"
    path.write_text('{"id": 2, "question": "How many endings?", "facts": [], '
                    '"pages": ["Ending 1: Shura", "Ending 4: Return"]}\n', encoding="utf-8")
    item = load_golden(path)[0]
    hits = [hit("Ending 4: Return"), hit("Emma"), hit("Ending 4: Return")]
    assert pages_found(item, hits) == ["Ending 4: Return"]
