from types import SimpleNamespace

from game_rag import config
from game_rag.answerer import NOT_COVERED, SYSTEM_PROMPT, Answerer, build_prompt, cited_numbers
from game_rag.chunker import Chunk
from game_rag.library import Hit


def hit(i, title, section, text):
    return Hit(chunk=Chunk(id=f"c{i}", text=text, page_title=title, section=section,
                           url=f"https://example.com/{i}", page_type="lore"), distance=0.2)


HITS = [
    hit(0, "Rot Essence", "Overview", "Dragonrot is the name of the illness that has gripped Ashina."),
    hit(1, "Emma", "Description", "Emma is a doctor serving a certain master."),
]


class FakeOllama:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content=self.reply))


def test_prompt_numbers_the_excerpts_and_ends_with_the_question():
    prompt = build_prompt("What is Dragonrot?", HITS)
    assert "[1] (Rot Essence > Overview)\nDragonrot is the name of the illness that has gripped Ashina." in prompt
    assert "[2] (Emma > Description)\nEmma is a doctor serving a certain master." in prompt
    assert prompt.rstrip().endswith("Question: What is Dragonrot?")


def test_system_prompt_has_the_fence_rules():
    assert "ONLY" in SYSTEM_PROMPT
    assert NOT_COVERED in SYSTEM_PROMPT
    assert "quote" in SYSTEM_PROMPT.lower()


def test_answer_makes_one_call_with_thinking_off():
    fake = FakeOllama('Dragonrot is an illness: "the illness that has gripped Ashina" [1]\n')
    answer = Answerer(client=fake).answer("What is Dragonrot?", HITS)
    assert answer == 'Dragonrot is an illness: "the illness that has gripped Ashina" [1]'
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["model"] == config.CHAT_MODEL
    assert call["think"] is False
    assert call["options"]["temperature"] == 0
    assert call["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert call["messages"][1]["content"] == build_prompt("What is Dragonrot?", HITS)
    assert "tools" not in call


def test_cited_numbers_finds_valid_excerpt_numbers():
    assert cited_numbers('a "x" [2] b "y" [1] c "z" [2]', how_many=2) == [1, 2]
    assert cited_numbers('made up "q" [7]', how_many=5) == []
    assert cited_numbers(NOT_COVERED, how_many=5) == []
