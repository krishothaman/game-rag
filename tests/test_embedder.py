from types import SimpleNamespace

from game_rag import config
from game_rag.embedder import Embedder


# pretends to be ollama, the "embedding" is just [length of text, 1.0]
class FakeOllama:
    def __init__(self):
        self.calls = []

    def embed(self, model, input):
        self.calls.append((model, input))
        texts = input if isinstance(input, list) else [input]
        return SimpleNamespace(embeddings=[[float(len(t)), 1.0] for t in texts])


def test_documents_are_sent_in_batches():
    fake = FakeOllama()
    vectors = Embedder(client=fake, batch_size=32).embed_documents([f"text {i}" for i in range(70)])
    assert len(vectors) == 70
    assert [len(batch) for _, batch in fake.calls] == [32, 32, 6]


def test_documents_go_in_plain_with_the_embedding_model():
    fake = FakeOllama()
    Embedder(client=fake).embed_documents(["Dragonrot spreads."])
    assert fake.calls == [(config.EMBED_MODEL, ["Dragonrot spreads."])]


def test_questions_get_the_instruction_in_front():
    fake = FakeOllama()
    vector = Embedder(client=fake).embed_query("What is Dragonrot?")
    sent = config.QUERY_INSTRUCTION + "What is Dragonrot?"
    assert fake.calls == [(config.EMBED_MODEL, sent)]
    assert vector == [float(len(sent)), 1.0]
