import json
from pathlib import Path

from game_rag.answerer import Answerer
from game_rag.chunker import chunk_page
from game_rag.library import Hit

page_file = next(Path("data/clean").glob("Rot_Essence-*.json"))
chunks = chunk_page(json.loads(page_file.read_text(encoding="utf-8")))
hits = [Hit(chunk=chunks[i], distance=0.0) for i in (0, 2, 3)]

questions = [
    "In Sekiro, what is Dragonrot and how is it cured?",
    "Who is Radahn?",
]

answerer = Answerer()
for question in questions:
    print(f"Q: {question}")
    print(answerer.answer(question, hits))
    print()
