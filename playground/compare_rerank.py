import time

from game_rag import config
from game_rag.embedder import Embedder
from game_rag.golden import load_golden, pages_found
from game_rag.library import Library
from game_rag.reranker import Reranker

libraries = {"hybrid": Library(Embedder()), "rerank": Library(Embedder(), reranker=Reranker())}
for name, path in [("dev", config.GOLDEN_FILE), ("held-out", config.HOLDOUT_FILE)]:
    qs = [q for q in load_golden(path) if not q.not_covered]
    for label, library in libraries.items():
        found, lines, started = 0, [], time.time()
        for q in qs:
            hits = library.search(q.question)
            got = pages_found(q, hits)
            found += bool(got)
            lines.append(f"   {'FOUND ' if got else 'MISSED'} #{q.id} {len(got)}/{len(q.pages)}  top: {', '.join(h.chunk.page_title for h in hits[:3])}")
        print(f"{name:8} {label}: {found}/{len(qs)}  ({(time.time() - started) / len(qs):.2f}s per question)")
        print("\n".join(lines))
