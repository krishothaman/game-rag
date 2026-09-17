from game_rag.chunker import Chunk
from game_rag.library import Library

VOCAB = ["dragonrot", "owl", "emma", "sword"]


class FakeEmbedder:
    def vector(self, text):
        words = text.lower().replace("?", "").replace(".", "").split()
        return [words.count(v) + 0.01 for v in VOCAB]

    def embed_documents(self, texts):
        return [self.vector(t) for t in texts]

    def embed_query(self, question):
        return self.vector(question)


def chunk(i, text, title):
    return Chunk(id=f"c{i}", text=text, page_title=title, section="Overview",
                 url=f"https://example.com/{i}", page_type="lore")


CHUNKS = [
    chunk(0, "Dragonrot spreads when Wolf dies. Dragonrot makes people cough.", "Rot Essence"),
    chunk(1, "Owl is the foster father of Wolf. Owl is a great shinobi.", "Owl"),
    chunk(2, "Emma is a doctor who helps Wolf.", "Emma"),
]


def test_search_returns_closest_chunk_first(tmp_path):
    library = Library(FakeEmbedder(), path=tmp_path)
    library.rebuild(CHUNKS, log=lambda m: None)
    hits = library.search("what is dragonrot?", k=2)
    assert hits[0].chunk.page_title == "Rot Essence"
    assert len(hits) == 2


def test_labels_survive_the_round_trip(tmp_path):
    library = Library(FakeEmbedder(), path=tmp_path)
    library.rebuild(CHUNKS, log=lambda m: None)
    hit = library.search("owl", k=1)[0]
    assert hit.chunk == CHUNKS[1]
    assert 0.0 < hit.similarity <= 1.0


def test_rebuild_replaces_old_chunks(tmp_path):
    library = Library(FakeEmbedder(), path=tmp_path)
    library.rebuild(CHUNKS, log=lambda m: None)
    library.rebuild(CHUNKS[:1], log=lambda m: None)
    assert library.count() == 1


def test_empty_library_finds_nothing(tmp_path):
    library = Library(FakeEmbedder(), path=tmp_path)
    assert library.count() == 0
    assert library.search("anything") == []


def test_rebuild_embeds_chunks_with_their_page_header(tmp_path):
    embedder = FakeEmbedder()
    seen = []
    embedder.embed_documents = lambda texts: seen.extend(texts) or [embedder.vector(t) for t in texts]
    Library(embedder, path=tmp_path).rebuild(CHUNKS, log=lambda m: None)
    assert seen[1] == "Owl > Overview\nOwl is the foster father of Wolf. Owl is a great shinobi."
