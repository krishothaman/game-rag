import math
import re
from collections import Counter

K1 = 1.5
B = 0.75
RRF_K = 60


def words(text):
    return [w for w in re.findall(r"[a-z0-9']+", text.lower()) if len(w) > 1]


class KeywordIndex:
    def __init__(self, docs):
        self.docs = [Counter(words(d)) for d in docs]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_length = sum(self.lengths) / max(1, len(self.docs))
        seen_in = Counter(w for d in self.docs for w in d)
        n = len(self.docs)
        # bm25 idf: a word in every doc is worth ~nothing, a rare one a lot
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in seen_in.items()}

    def score(self, query_words, i):
        doc, length = self.docs[i], self.lengths[i]
        total = 0.0
        for w in query_words:
            tf = doc.get(w, 0)
            if tf:
                total += self.idf[w] * tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / self.avg_length))
        return total

    def top(self, query, k):
        q = set(words(query))
        scored = [(self.score(q, i), i) for i in range(len(self.docs))]
        return [i for s, i in sorted(scored, key=lambda x: -x[0]) if s > 0][:k]


def fuse(rankings):
    # reciprocal rank fusion: only the positions matter, so the two kinds of score never need comparing
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0) + 1 / (RRF_K + rank)
    return sorted(scores, key=lambda item: -scores[item])
