from game_rag import config
from game_rag.embedder import Embedder
from game_rag.golden import load_golden, pages_found
from game_rag.library import Library

library = Library(Embedder())
for name, path in [("dev", config.GOLDEN_FILE), ("held-out", config.HOLDOUT_FILE)]:
    qs = [q for q in load_golden(path) if not q.not_covered]
    for hybrid in (False, True):
        found, lines = 0, []
        for q in qs:
            hits = library.search(q.question, hybrid=hybrid)
            got = pages_found(q, hits)
            found += bool(got)
            lines.append(f"   {'FOUND ' if got else 'MISSED'} #{q.id} {len(got)}/{len(q.pages)}  top: {', '.join(h.chunk.page_title for h in hits[:3])}")
        print(f"{name:8} {'hybrid ' if hybrid else 'meaning'}: {found}/{len(qs)}")
        print("\n".join(lines))
