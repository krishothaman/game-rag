import json

from game_rag import config
from game_rag.cleaner import clean_all
from game_rag.cli import main
from game_rag.measure import measure
from game_rag.titles import file_stem, page_url


def write_raw(raw_dir, requested, title, html):
    data = {"requested_title": requested, "title": title, "url": page_url(title),
            "html": html, "categories": ["Key Items"]}
    (raw_dir / f"{file_stem(requested)}.json").write_text(json.dumps(data), encoding="utf-8")


def write_clean(clean_dir, title, texts, categories):
    page = {"title": title, "url": page_url(title), "categories": categories,
            "sections": [{"heading": f"Part {i}", "level": 2, "text": t} for i, t in enumerate(texts)]}
    (clean_dir / f"{file_stem(title)}.json").write_text(json.dumps(page), encoding="utf-8")


def test_clean_all_skips_redirect_duplicates_and_empty_pages(tmp_path):
    raw, clean = tmp_path / "raw", tmp_path / "clean"
    raw.mkdir()
    write_raw(raw, "Rot Essence", "Rot Essence", "<h2>Overview</h2><p>Dragonrot spreads.</p>")
    # dragonrot redirects to rot essence so this one is a duplicate
    write_raw(raw, "Dragonrot", "Rot Essence", "<h2>Overview</h2><p>Dragonrot spreads.</p>")
    write_raw(raw, "Stub", "Stub", "<table><tr><td>navigation only</td></tr></table>")
    report = clean_all(raw, clean)
    assert report.written == ["Rot Essence"]
    assert len(report.duplicates) == 1
    assert report.empty == ["Stub"]
    files = list(clean.glob("*.json"))
    assert len(files) == 1
    page = json.loads(files[0].read_text(encoding="utf-8"))
    assert page["sections"] == [{"heading": "Overview", "level": 2, "text": "Dragonrot spreads."}]


def test_measure_counts_pages_sections_and_words(tmp_path):
    write_clean(tmp_path, "Owl", ["one two three", "four five"], ["Characters"])
    write_clean(tmp_path, "Emma", ["one"], ["Characters", "Dialogues"])
    stats = measure(tmp_path)
    assert stats["pages"] == 2
    assert stats["sections"] == 3
    assert stats["total_words"] == 6
    assert stats["average_words_per_page"] == 3
    assert stats["median_words_per_page"] == 3
    assert stats["largest_pages"][0] == {"title": "Owl", "words": 5}
    assert stats["smallest_pages"][0] == {"title": "Emma", "words": 1}
    assert stats["pages_per_category"] == {"Characters": 2, "Dialogues": 1}


def test_measure_handles_an_empty_folder(tmp_path):
    stats = measure(tmp_path)
    assert stats["pages"] == 0
    assert stats["total_words"] == 0


def test_show_prints_a_clean_page(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "CLEAN_DIR", tmp_path)
    write_clean(tmp_path, "Owl", ["Owl is a great shinobi."], ["Characters"])
    assert main(["show", "Owl"]) == 0
    out = capsys.readouterr().out
    assert "## Part 0" in out
    assert "Owl is a great shinobi." in out


def test_show_reports_a_missing_page(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "CLEAN_DIR", tmp_path)
    assert main(["show", "Nobody"]) == 1
    assert "not found" in capsys.readouterr().out
