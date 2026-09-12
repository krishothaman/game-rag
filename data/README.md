# Data

- `raw/`: raw page downloads. Not committed, recreate with `uv run python -m game_rag collect`.
- `clean/`: cleaned text of Sekiro lore pages, one JSON file per page.
- `stats.json`: page and word counts from `uv run python -m game_rag stats`.

The wiki text in this folder comes from the [Sekiro: Shadows Die Twice Fandom wiki](https://sekiro-shadows-die-twice.fandom.com/) and its contributors. It's licensed [CC BY-SA](https://www.fandom.com/licensing) and shared here under the same license. Every page keeps a link to where it came from.

Unofficial fan project. Not affiliated with FromSoftware or Activision.
