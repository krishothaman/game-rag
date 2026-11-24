import sys
import time

from game_rag import config
from game_rag.answerer import NOT_COVERED, Answerer
from game_rag.embedder import Embedder
from game_rag.golden import load_golden, load_verdicts, verdict_key
from game_rag.library import Library

holdout = "--holdout" in sys.argv
model = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--model=")), config.CHAT_MODEL)
golden_file = config.HOLDOUT_FILE if holdout else config.GOLDEN_FILE
verdicts_file = config.HOLDOUT_VERDICTS_FILE if holdout else config.VERDICTS_FILE

questions = load_golden(golden_file)
library = Library(Embedder())
# search everything first so the embedder and the chat model don't keep swapping on the gpu
hits_for = {q.id: library.search(q.question) for q in questions}

answerer = Answerer(model=model)
verdicts = load_verdicts(verdicts_file)
started = time.time()
for q in questions:
    hits = hits_for[q.id]
    answer = answerer.answer(q.question, hits)
    known = verdicts.get(verdict_key(q, answer))
    print(f"\n=== #{q.id} {q.question}")
    print(f"ANSWER: {answer}")
    print(f"PAGES:  {', '.join(h.chunk.page_title for h in hits)}")
    print(f"SHOULD: {NOT_COVERED if q.not_covered else '; '.join(q.facts)}")
    print(f"KNOWN:  {'-' if known is None else ('y' if known else 'n')}")
print(f"\nMODEL {model}: {len(questions)} answers in {time.time() - started:.0f}s")
