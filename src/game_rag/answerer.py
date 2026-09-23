import re

import ollama

from game_rag import config

NOT_COVERED = "My library doesn't cover that."

SYSTEM_PROMPT = f"""You answer questions about the lore of the game Sekiro: Shadows Die Twice.

Rules:
- Use ONLY the numbered wiki excerpts in the user's message. Do not use anything you already know about Sekiro.
- Every sentence of your answer must contain an exact quote from an excerpt, copied word for word in double quotes, followed by the excerpt number in brackets. Example: Wolf serves Kuro: "Wolf is a shinobi sworn to protect Kuro" [2]
- Keep who did what to whom exactly as the excerpt has it. Read the quote again before you write the sentence around it: if the excerpt says A did something to B, never write that B did it to A.
- Never say something did NOT happen unless an excerpt says so in those words. Missing from the excerpts is not the same as untrue, and that case is covered by the line below.
- Add nothing the excerpts don't state, even if you are sure it's true.
- If the excerpts don't contain the answer, reply with exactly this and nothing else: {NOT_COVERED}
- Keep it short, a few sentences at most."""


def build_prompt(question, hits):
    parts = ["Wiki excerpts:\n"]
    for i, h in enumerate(hits, start=1):
        parts.append(f"[{i}] ({h.chunk.page_title} > {h.chunk.section})\n{h.chunk.text}\n")
    parts.append(f"Question: {question}")
    return "\n".join(parts)


def cited_numbers(answer, how_many):
    found = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    return sorted(n for n in found if 1 <= n <= how_many)


class Answerer:
    def __init__(self, client=None, model=config.CHAT_MODEL):
        self.client = client if client is not None else ollama.Client()
        self.model = model

    def answer(self, question, hits):
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(question, hits)},
            ],
            think=False,
            options={"temperature": 0},
        )
        return response.message.content.strip()
