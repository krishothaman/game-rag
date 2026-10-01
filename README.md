# game_rag

Ask questions about Sekiro: Shadows Die Twice lore and get answers quoted and cited from the fan wiki. Everything runs on your own machine with open models through [Ollama](https://ollama.com), so there's no API key and nothing to pay for.

A learning project: it's built level by level, and every change gets measured against a set of test questions. See [`docs/progress.md`](docs/progress.md) for what changed and what it did to the scores.

## Setup

You need Python 3.12+, [uv](https://docs.astral.sh/uv/) and Ollama.

```bash
uv sync
ollama pull qwen3.5:4b
ollama pull qwen3-embedding:0.6b
uv run python -m game_rag index
```

`index` takes about half a minute. The cleaned wiki pages are already in the repo, so you don't need to download anything else.

## Use it

```bash
uv run python -m game_rag ask "Who is the Sculptor?"
uv run python -m game_rag ask "Who is the Sculptor?" --debug   # also show the wiki chunks it found
uv run python -m game_rag chat                                 # keep asking until you type exit
```

Add `--model <name>` to `ask`, `chat` or `score` to answer with a different Ollama model.

If the wiki doesn't cover something, it says so instead of making it up.

## How it works

1. Wiki pages are cleaned into text sections (strategy, trivia and cut content are dropped).
2. Sections are packed into chunks of up to 300 words, each labelled with its page and section.
3. Chunks are embedded with `qwen3-embedding:0.6b` and stored in ChromaDB.
4. A question is searched two ways, by meaning (embeddings) and by keywords (BM25), and the two rankings are merged.
5. The top 5 chunks go to `qwen3.5:4b`, which has to answer only from them, quoting and citing `[n]`.

## Measuring it

```bash
uv run python -m game_rag score             # did the right wiki page reach the top 5?
uv run python -m game_rag score --answers   # also answer each question and judge it y/n
uv run python -m game_rag score --holdout   # the locked questions, only at the end of a level
```

Your y/n verdicts are remembered, so a rerun only asks about answers that changed.

## Rebuilding the data

```bash
uv run python -m game_rag collect   # download the wiki pages (polite, about one request a second)
uv run python -m game_rag clean
uv run python -m game_rag index
```

## Tests

```bash
uv run pytest
```

## Credits

Lore text comes from the [Sekiro: Shadows Die Twice Fandom wiki](https://sekiro-shadows-die-twice.fandom.com/) and its contributors, under [CC BY-SA](https://www.fandom.com/licensing). Unofficial fan project, not affiliated with FromSoftware or Activision.
