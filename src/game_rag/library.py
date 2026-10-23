from dataclasses import asdict, dataclass

import chromadb
from chromadb.config import Settings

from game_rag import config
from game_rag.chunker import Chunk
from game_rag.keywords import KeywordIndex, fuse


@dataclass
class Hit:
    chunk: Chunk
    distance: float

    @property
    def similarity(self):
        return 1 - self.distance


class Library:
    def __init__(self, embedder, path=config.LIBRARY_DIR, name=config.COLLECTION, reranker=None):
        self.embedder = embedder
        self.reranker = reranker
        self.client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}, embedding_function=None,
        )
        self.keywords = None

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
                embeddings=self.embedder.embed_documents([c.embed_text for c in part]),
                metadatas=labels,
            )
            log(f"  embedded {min(i + batch, len(chunks))}/{len(chunks)} chunks")
        self.keywords = None

    def search(self, question, k=config.TOP_K, hybrid=config.HYBRID):
        total = self.count()
        if total == 0:
            return []
        # rank every chunk by meaning, it's only ~600 so that's cheap
        result = self.collection.query(
            query_embeddings=[self.embedder.embed_query(question)],
            n_results=total,
            include=["documents", "metadatas", "distances"],
        )
        found = zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0])
        hits = {i: Hit(chunk=Chunk(id=i, text=text, **meta), distance=d) for i, text, meta, d in found}
        ranking = list(hits)
        if hybrid:
            ranking = fuse([ranking[:config.FUSE_DEPTH], self.keyword_ranking(question, hits)])
        if self.reranker is None:
            return [hits[i] for i in ranking[:k]]
        return self.rerank(question, [hits[i] for i in ranking[:config.RERANK_DEPTH]], k)

    def rerank(self, question, candidates, k):
        scores = self.reranker.scores(question, [h.chunk.embed_text for h in candidates])
        order = sorted(range(len(candidates)), key=lambda n: -scores[n])
        return [candidates[n] for n in order[:k]]

    def keyword_ranking(self, question, hits):
        if self.keywords is None:
            self.keyword_ids = sorted(hits)
            docs = [hits[i].chunk.embed_text for i in self.keyword_ids]
            self.keywords = KeywordIndex(docs)
        return [self.keyword_ids[n] for n in self.keywords.top(question, config.FUSE_DEPTH)]
