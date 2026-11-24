import math

from game_rag.embedder import Embedder


def similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


question = "Who is Radahn?"
sentences = [
    "He is a character from elden ring",
    "Final boss of sekiro",
    "Elden ring : Shadow of the Erdtree",
    "Its so fun playing Elder Scrolls",
]

e = Embedder()
q = e.embed_query(question)
vectors = e.embed_documents(sentences)

print(f"one embedding = {len(q)} numbers. first 5: {[round(x, 3) for x in q[:5]]}\n")
print(f"question: {question}\n")
for s, v in sorted(zip(sentences, vectors), key=lambda pair: -similarity(q, pair[1])):
    print(f"{similarity(q, v):.2f}  {s}")
