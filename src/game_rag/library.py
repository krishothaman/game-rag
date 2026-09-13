from dataclasses import asdict, dataclass

import chromadb
from chromadb.config import Settings

from game_rag import config
from game_rag.chunker import Chunk


@dataclass
class Hit:
    chunk: Chunk
    distance: float

    @property
    def similarity(self):
        return 1 - self.distance


class Library:
    def __init__(self, embedder, path=config.LIBRARY_DIR, name=config.COLLECTION):
        self.embedder = embedder
        self.client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}, embedding_function=None,
        )

    def count(self):
        return self.collection.count()

    def rebuild(self, chunks, log=print):
        old_ids = self.collection.get(include=[])["ids"]
        if old_ids:
            self.collection.delete(ids=old_ids)

        batch = 100
        for i in range(0, len(chunks), batch):
            part = chunks[i:i + batch]
            texts = [c.text for c in part]
            labels = [{k: v for k, v in asdict(c).items() if k not in ("id", "text")} for c in part]
            self.collection.add(
                ids=[c.id for c in part],
                documents=texts,
                embeddings=self.embedder.embed_documents(texts),
                metadatas=labels,
            )
            log(f"  embedded {min(i + batch, len(chunks))}/{len(chunks)} chunks")

    def search(self, question, k=config.TOP_K):
        total = self.count()
        if total == 0:
            return []
        result = self.collection.query(
            query_embeddings=[self.embedder.embed_query(question)],
            n_results=min(k, total),
            include=["documents", "metadatas", "distances"],
        )
        found = zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0])
        return [Hit(chunk=Chunk(id=i, text=text, **meta), distance=d) for i, text, meta, d in found]
