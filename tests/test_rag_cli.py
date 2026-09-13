from game_rag import cli
from game_rag.chunker import Chunk
from game_rag.library import Hit


def hit(i, title, section, text):
    return Hit(chunk=Chunk(id=f"c{i}", text=text, page_title=title, section=section,
                           url=f"https://example.com/{title}", page_type="lore"), distance=0.25)


class FakeLibrary:
    def __init__(self, hits):
        self.hits = hits

    def count(self):
        return len(self.hits)

    def search(self, question, k=5):
        return self.hits


class FakeAnswerer:
    def __init__(self, reply=None, error=None):
        self.reply, self.error = reply, error

    def answer(self, question, hits):
        if self.error:
            raise self.error
        return self.reply


HITS = [
    hit(0, "Rot Essence", "Overview", "Dragonrot is the name of the illness that has gripped Ashina."),
    hit(1, "Emma", "Description", "Emma is a doctor."),
]


def test_ask_prints_the_answer_and_only_the_cited_sources(capsys):
    answerer = FakeAnswerer('An illness: "the illness that has gripped Ashina" [1]')
    assert cli.answer_question("What is Dragonrot?", FakeLibrary(HITS), answerer) == 0
    out = capsys.readouterr().out
    assert 'An illness: "the illness that has gripped Ashina" [1]' in out
    assert "[1] Rot Essence > Overview  https://example.com/Rot Essence" in out
    assert "Emma" not in out


def test_debug_mode_shows_every_retrieved_chunk(capsys):
    answerer = FakeAnswerer('An illness: "the illness that has gripped Ashina" [1]')
    cli.answer_question("What is Dragonrot?", FakeLibrary(HITS), answerer, debug=True)
    out = capsys.readouterr().out
    assert "similarity 0.75" in out
    assert "Emma is a doctor." in out


def test_ask_with_empty_library_says_to_run_index(monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_library", lambda: FakeLibrary([]))
    monkeypatch.setattr(cli, "make_answerer", lambda: FakeAnswerer("unused"))
    assert cli.main(["ask", "What is Dragonrot?"]) == 1
    assert "index" in capsys.readouterr().out


def test_ollama_not_running_gets_a_friendly_message(monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_library", lambda: FakeLibrary(HITS))
    monkeypatch.setattr(cli, "make_answerer", lambda: FakeAnswerer(error=ConnectionError("nope")))
    assert cli.main(["ask", "What is Dragonrot?"]) == 1
    assert "Ollama" in capsys.readouterr().out
