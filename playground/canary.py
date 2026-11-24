import sys

from game_rag import config
from game_rag.answerer import NOT_COVERED, Answerer
from game_rag.chunker import Chunk
from game_rag.library import Hit


def hit(title, section, text):
    return Hit(chunk=Chunk(id=title, text=text, page_title=title, section=section,
                           url="https://example.com", page_type="character"), distance=0.3)


FILLER = [
    hit("Ashina Castle", "Overview", "Ashina Castle is the seat of the Ashina Clan, built atop a hill overlooking the land."),
    hit("Kuro", "Description", "Kuro is the Divine Heir, a young lord who carries the Dragon's Heritage."),
]

# (question, excerpts, a word the answer must contain, or None if it must refuse)
CANARIES = [
    ("What is Emma's favourite food?",
     [hit("Emma", "Trivia", "Emma's favourite food is roasted chestnuts, which Dogen used to buy for her.")] + FILLER,
     "chestnut"),
    ("What colour is the Sculptor's scarf?",
     [hit("Sculptor", "Appearance", "The Sculptor always wears a faded green scarf that Kingfisher gave him.")] + FILLER,
     "green"),
    ("Who did Owl fight in the duel at Hirata Estate?",
     [hit("Owl", "History", "At Hirata Estate, Owl fought Kuro in a duel and lost.")] + FILLER,
     "kuro"),
    ("What is the name of Wolf's horse?", FILLER, None),
    ("How old is Isshin Ashina?", FILLER, None),
]


def main():
    model = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--model=")), config.CHAT_MODEL)
    answerer = Answerer(model=model)
    passed = 0
    for question, hits, must_say in CANARIES:
        answer = answerer.answer(question, hits)
        ok = NOT_COVERED in answer if must_say is None else must_say in answer.lower()
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {question}\n      {answer}\n")
    print(f"{model}: {passed}/{len(CANARIES)} canaries alive")


main()
