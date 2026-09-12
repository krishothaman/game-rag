# Level 0 — Get the Data: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Download the Sekiro wiki's lore pages politely, turn them into clean text sections, and measure how big the data really is.

**Architecture:** Three small parts from the spec: the **Collector** (downloads raw pages through the wiki's public API, resumable), the **Cleaner** (HTML → plain-text sections, with navigation, images, and dropped sections removed), and a **measure** step (page and word counts). A small command-line tool runs each step: `uv run python -m game_rag <collect|clean|stats|show>`.

**Tech Stack:** Python 3.12 (managed by `uv`), `requests`, `beautifulsoup4`, `pytest`. All free and open source.

**Spec:** `docs/superpowers/specs/2026-09-12-game-rag-design.md`

## Global Constraints

- **Zero cost (spec 1.1):** only free, open-source packages from PyPI. No paid services, no API keys, no accounts.
- **Git (owner's rule):** the owner makes every commit. An agent executing this plan must **never** run `git add`, `git commit`, or `git push`. At each "Commit (owner)" step, stop and show the owner the exact commands.
- **Code style (owner's rule):** the code must not look AI-generated. Only comment where something isn't obvious, in short casual lowercase style (e.g. `# wiki sends big lists in chunks, keep asking till done`). No formal docstrings, no spec references in code. The code blocks below show the logic; write them in this style.
- **Politeness (spec 4.2):** no faster than one request per second (`REQUEST_DELAY_SECONDS = 1.1`), with a descriptive User-Agent.
- **Only the official API:** use `https://sekiro-shadows-die-twice.fandom.com/api.php` only. The wiki's normal web pages sit behind a bot check; never try to get around it.
- **License (spec 4.6):** the wiki text is CC BY-SA. Every saved page keeps its URL, and `data/README.md` credits the Sekiro Fandom wiki.
- **Scope (spec 4.1):** lore categories only. Boss strategy guides, walkthroughs, and trivia/speculation sections are left out.
- **Python version:** 3.12, pinned with `uv python pin 3.12`.
- Run every command from the project folder: `C:\projects\RAGMODEL`.

## Facts checked on 2026-09-12 (so nobody has to re-guess)

- The wiki has **415 articles**; the license reported by its API is **CC-BY-SA**.
- The 10 lore categories below contain **276 unique pages** (download ≈ 6–8 minutes).
- `Special:Statistics` (where a database download link would be) is behind a bot check, so per spec 4.2 we use the public API instead.
- Asking for `Dragonrot` returns the page `Rot Essence` (a **redirect**), so the Collector records the final title.
- Rendered pages contain navigation tables before the first heading, `aside.portable-infobox` info boxes, `.wikia-gallery` galleries, `.tabber` tabs (labels in `.wds-tabs__wrapper`, content in `.wds-tab__content`), and dialogue tables (`table.article-table`).

## File Structure

```
pyproject.toml                    project settings and dependencies (uv)
.python-version                   pins Python 3.12 (created by uv)
uv.lock                           exact package versions (created by uv)
src/game_rag/__init__.py       marks the package
src/game_rag/config.py         all settings: API URL, categories, delays, folders
src/game_rag/titles.py         page title → wiki URL, page title → safe file name
src/game_rag/wiki_client.py    polite API client (category lists, rendered pages, retries)
src/game_rag/collector.py      Collector: download every lore page, resumable
src/game_rag/cleaner.py        Cleaner: HTML → clean sections; clean_all for the folder
src/game_rag/measure.py        page/section/word statistics
src/game_rag/cli.py            the command-line tool
src/game_rag/__main__.py       lets `python -m game_rag` run the tool
tests/test_titles.py
tests/test_wiki_client.py
tests/test_collector.py
tests/test_cleaner.py
tests/test_pipeline.py            clean_all, measure, and CLI tests
data/raw/                         raw downloads (NOT committed; recreate with `collect`)
data/clean/                       clean pages (committed, CC BY-SA)
data/stats.json                   measurements (committed)
data/README.md                    data credit and license
docs/level-0-notes.md             the owner's observations about the data
```

---

## Before Task 1 (owner): first commit and connect GitHub

- [ ] On github.com, create a new, **empty** repository (for example `game-rag`). Do **not** tick "Add a README", ".gitignore", or "license"; those would clash with the local files.
- [ ] Commit the spec, this plan, and `.gitignore`, connect the repository, and push (replace `<you>` with your GitHub username):

```bash
git add .gitignore docs
git commit -m "docs: add game_rag design spec and Level 0 plan"
git remote add origin https://github.com/<you>/game-rag.git
git push -u origin main
```

The first push opens a browser window to sign in to GitHub (Git for Windows includes this).

---

### Task 1: Project setup and title helpers

*Why:* every later part needs a working Python project, one place for settings, and a safe way to turn page titles into links and file names.

**Files:**
- Create: `pyproject.toml`, `src/game_rag/__init__.py`, `src/game_rag/config.py`, `src/game_rag/titles.py`, `tests/test_titles.py`
- Modify: `.gitignore`
- Created by uv: `.python-version`, `uv.lock`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `game_rag.titles.page_url(title: str) -> str`: public wiki URL for a title.
  - `game_rag.titles.file_stem(title: str) -> str`: safe, unique file name (no extension).
  - `game_rag.config`: `API_URL`, `USER_AGENT`, `REQUEST_DELAY_SECONDS`, `LORE_CATEGORIES`, `DROPPED_SECTIONS`, `PROJECT_ROOT`, `RAW_DIR`, `CLEAN_DIR`, `STATS_FILE`.

- [ ] **Step 1: Pin Python 3.12**

Run: `uv python pin 3.12`
Expected: `Pinned .python-version to 3.12` (uv downloads Python 3.12 if needed; it's free).

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "game-rag"
version = "0.1.0"
description = "game_rag: a free, open-model RAG learning project"
requires-python = ">=3.12"
dependencies = []

[build-system]
requires = ["uv_build>=0.9.0,<0.13.0"]
build-backend = "uv_build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create the package marker `src/game_rag/__init__.py`**

```python
"""game_rag: a free, open-model RAG learning project."""
```

- [ ] **Step 4: Add the packages**

Run: `uv add requests beautifulsoup4`
Then: `uv add --dev pytest`
Expected: both finish without errors; `pyproject.toml` now lists the packages and `uv.lock` exists.

- [ ] **Step 5: Keep raw downloads out of git.** Append to `.gitignore`:

```gitignore

# Raw wiki downloads: large and re-creatable with `uv run python -m game_rag collect`
data/raw/
*.tmp
```

- [ ] **Step 6: Create `src/game_rag/config.py`**

```python
"""All project settings in one place (spec sections 4.1 and 4.2)."""
from pathlib import Path

API_URL = "https://sekiro-shadows-die-twice.fandom.com/api.php"
USER_AGENT = "game_rag/0.1 (free open-source RAG learning project)"
REQUEST_DELAY_SECONDS = 1.1  # spec 4.2: no faster than one request per second

# Wiki categories that hold lore (spec 4.1). Bosses/strategy pages are left out on purpose.
LORE_CATEGORIES = [
    "Lore",
    "Characters",
    "Endings",
    "Key Items",
    "Prosthetic Tools",
    "Memories",
    "Locations",
    "Chapters",
    "Dialogue",
    "Dialogues",
]

# Section headings (lowercase) whose text is left out for now (spec 4.1),
# plus sections that never contain lore text.
DROPPED_SECTIONS = {
    "trivia",
    "speculation",
    "strategy",
    "strategies",
    "walkthrough",
    "gallery",
    "video",
    "videos",
    "references",
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
STATS_FILE = PROJECT_ROOT / "data" / "stats.json"
```

- [ ] **Step 7: Write the failing tests `tests/test_titles.py`**

```python
from game_rag.titles import file_stem, page_url

BASE = "https://sekiro-shadows-die-twice.fandom.com/wiki/"


def test_page_url_replaces_spaces_with_underscores():
    assert page_url("Great Shinobi - Owl") == BASE + "Great_Shinobi_-_Owl"


def test_page_url_keeps_subpage_slash_colon_and_brackets():
    assert page_url("Emma/Dialogue") == BASE + "Emma/Dialogue"
    assert page_url("Ending 1: Shura") == BASE + "Ending_1:_Shura"
    assert page_url("Owl (Father)") == BASE + "Owl_(Father)"


def test_page_url_encodes_unusual_characters():
    assert page_url("Kuro's Charm") == BASE + "Kuro's_Charm"
    assert page_url("Café") == BASE + "Caf%C3%A9"


def test_file_stem_is_readable_and_safe():
    stem = file_stem("Emma/Dialogue")
    assert stem.startswith("Emma_Dialogue-")
    assert len(stem) == len("Emma_Dialogue-") + 8


def test_file_stem_is_unique_and_repeatable():
    assert file_stem("Emma/Dialogue") != file_stem("Emma Dialogue")
    assert file_stem("Owl") == file_stem("Owl")
```

- [ ] **Step 8: Run the tests and check they fail**

Run: `uv run pytest tests/test_titles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game_rag.titles'`

- [ ] **Step 9: Create `src/game_rag/titles.py`**

```python
"""Turn wiki page titles into public URLs and safe file names."""
import hashlib
import re
from urllib.parse import quote

WIKI_BASE_URL = "https://sekiro-shadows-die-twice.fandom.com/wiki/"


def page_url(title: str) -> str:
    """Return the public wiki URL for a page title."""
    return WIKI_BASE_URL + quote(title.replace(" ", "_"), safe="/:()'-,._!")


def file_stem(title: str) -> str:
    """Return a safe, unique file name (without extension) for a page title.

    The readable part helps humans; the short hash keeps titles like
    "Emma/Dialogue" and "Emma Dialogue" from overwriting each other.
    """
    readable = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_") or "page"
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"
```

- [ ] **Step 10: Run the tests and check they pass**

Run: `uv run pytest tests/test_titles.py -v`
Expected: `5 passed`

- [ ] **Step 11: Commit (owner)**

```bash
git add pyproject.toml uv.lock .python-version .gitignore src tests
git commit -m "feat: set up project with config and title helpers"
git push
```

---

### Task 2: Polite wiki client

*Why:* every download goes through one careful part that waits between requests, retries when the wiki is busy, and follows redirects.

**Files:**
- Create: `src/game_rag/wiki_client.py`, `tests/test_wiki_client.py`

**Interfaces:**
- Consumes: `config.API_URL`, `config.USER_AGENT`, `config.REQUEST_DELAY_SECONDS`, `titles.page_url`.
- Produces:
  - `class WikiError(Exception)`
  - `@dataclass RawPage(requested_title: str, title: str, url: str, html: str, categories: list[str])`
  - `WikiClient(session=None, delay_seconds=1.1, max_attempts=3, sleep=time.sleep)`
  - `WikiClient.get_category_members(category: str) -> list[str]`: main-article titles in `Category:<category>`.
  - `WikiClient.get_page(title: str) -> RawPage`: rendered HTML, with redirects followed.

- [ ] **Step 1: Write the failing tests `tests/test_wiki_client.py`**

```python
import pytest
import requests

from game_rag import config
from game_rag.wiki_client import WikiClient, WikiError


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


class FakeSession:
    """Stands in for requests.Session so tests never touch the internet."""

    def __init__(self, responses):
        self.headers = {}
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_client(responses, sleeps=None):
    session = FakeSession(responses)
    recorded = sleeps if sleeps is not None else []
    client = WikiClient(session=session, delay_seconds=1.1, max_attempts=3, sleep=recorded.append)
    return client, session


PAGE_PAYLOAD = {
    "parse": {
        "title": "Rot Essence",
        "text": "<p>Dragonrot</p>",
        "categories": [{"category": "Key_Items"}, {"category": "Items"}],
    }
}


def test_sets_a_descriptive_user_agent():
    _, session = make_client([])
    assert session.headers["User-Agent"] == config.USER_AGENT


def test_category_members_follows_continue_tokens():
    first = FakeResponse(payload={
        "query": {"categorymembers": [{"title": "Ashina"}, {"title": "Owl"}]},
        "continue": {"cmcontinue": "page|X", "continue": "-||"},
    })
    second = FakeResponse(payload={"query": {"categorymembers": [{"title": "Emma"}]}})
    client, session = make_client([first, second])
    assert client.get_category_members("Characters") == ["Ashina", "Owl", "Emma"]
    assert session.calls[0]["cmtitle"] == "Category:Characters"
    assert session.calls[1]["cmcontinue"] == "page|X"


def test_get_page_follows_redirect_and_cleans_category_names():
    client, session = make_client([FakeResponse(payload=PAGE_PAYLOAD)])
    page = client.get_page("Dragonrot")
    assert page.requested_title == "Dragonrot"
    assert page.title == "Rot Essence"
    assert page.url == "https://sekiro-shadows-die-twice.fandom.com/wiki/Rot_Essence"
    assert page.html == "<p>Dragonrot</p>"
    assert page.categories == ["Key Items", "Items"]
    assert session.calls[0]["redirects"] == "1"


def test_waits_before_every_request():
    sleeps = []
    client, _ = make_client([FakeResponse(payload=PAGE_PAYLOAD), FakeResponse(payload=PAGE_PAYLOAD)], sleeps)
    client.get_page("A")
    client.get_page("B")
    assert sleeps == [1.1, 1.1]


def test_retries_after_server_error_and_network_error():
    sleeps = []
    responses = [FakeResponse(status_code=503), requests.ConnectionError("offline"), FakeResponse(payload=PAGE_PAYLOAD)]
    client, session = make_client(responses, sleeps)
    assert client.get_page("Rot Essence").title == "Rot Essence"
    assert len(session.calls) == 3
    assert sleeps == pytest.approx([1.1, 2.2, 3.3])


def test_gives_up_after_three_failed_attempts():
    client, session = make_client([FakeResponse(status_code=503)] * 3)
    with pytest.raises(WikiError, match="gave up after 3 attempts"):
        client.get_page("Owl")
    assert len(session.calls) == 3


def test_wiki_error_reply_fails_immediately_without_retry():
    reply = FakeResponse(payload={"error": {"code": "missingtitle", "info": "The page you specified doesn't exist."}})
    client, session = make_client([reply])
    with pytest.raises(WikiError, match="doesn't exist"):
        client.get_page("Not A Page")
    assert len(session.calls) == 1
```

- [ ] **Step 2: Run the tests and check they fail**

Run: `uv run pytest tests/test_wiki_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game_rag.wiki_client'`

- [ ] **Step 3: Create `src/game_rag/wiki_client.py`**

```python
"""A small, polite client for the Sekiro Fandom wiki's public API (spec 4.2)."""
import time
from dataclasses import dataclass

import requests

from game_rag import config
from game_rag.titles import page_url


class WikiError(Exception):
    """The wiki could not give us what we asked for."""


@dataclass
class RawPage:
    requested_title: str
    title: str
    url: str
    html: str
    categories: list[str]


class WikiClient:
    def __init__(self, session=None, delay_seconds=config.REQUEST_DELAY_SECONDS,
                 max_attempts=3, sleep=time.sleep):
        self.session = session if session is not None else requests.Session()
        self.session.headers["User-Agent"] = config.USER_AGENT
        self.delay_seconds = delay_seconds
        self.max_attempts = max_attempts
        self.sleep = sleep

    def get_category_members(self, category: str) -> list[str]:
        """Return the titles of all main articles in Category:<category>."""
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmnamespace": "0",
            "cmlimit": "500",
        }
        titles = []
        while True:
            data = self._get(params)
            titles.extend(member["title"] for member in data["query"]["categorymembers"])
            if "continue" not in data:
                return titles
            params = {**params, **data["continue"]}

    def get_page(self, title: str) -> RawPage:
        """Return a page's rendered HTML, following redirects (e.g. Dragonrot -> Rot Essence)."""
        data = self._get({
            "action": "parse",
            "page": title,
            "prop": "text|categories",
            "redirects": "1",
            "disableeditsection": "1",
            "disablelimitreport": "1",
        })
        parsed = data["parse"]
        final_title = parsed["title"]
        return RawPage(
            requested_title=title,
            title=final_title,
            url=page_url(final_title),
            html=parsed["text"],
            categories=[c["category"].replace("_", " ") for c in parsed.get("categories", [])],
        )

    def _get(self, params: dict) -> dict:
        full_params = {**params, "format": "json", "formatversion": "2"}
        last_problem = "no attempts made"
        for attempt in range(1, self.max_attempts + 1):
            self.sleep(self.delay_seconds * attempt)  # polite pause, longer on each retry
            try:
                response = self.session.get(config.API_URL, params=full_params, timeout=30)
            except requests.RequestException as err:
                last_problem = f"network error: {err}"
                continue
            if response.status_code == 429 or response.status_code >= 500:
                last_problem = f"HTTP {response.status_code}"
                continue
            if response.status_code >= 400:
                raise WikiError(f"HTTP {response.status_code}")
            data = response.json()
            if "error" in data:
                raise WikiError(data["error"].get("info", "unknown wiki error"))
            return data
        raise WikiError(f"gave up after {self.max_attempts} attempts: {last_problem}")
```

- [ ] **Step 4: Run the tests and check they pass**

Run: `uv run pytest tests/test_wiki_client.py -v`
Expected: `7 passed`

- [ ] **Step 5: Commit (owner)**

```bash
git add src/game_rag/wiki_client.py tests/test_wiki_client.py
git commit -m "feat: add polite wiki API client with retries and redirects"
git push
```

---

### Task 3: Collector

*Why:* downloads every lore page once, saves it as a raw copy, and can safely continue after an interruption (spec 3.1 part 1 and 7.1).

**Files:**
- Create: `src/game_rag/collector.py`, `tests/test_collector.py`

**Interfaces:**
- Consumes: `WikiClient.get_category_members`, `WikiClient.get_page`, `RawPage`, `WikiError`, `titles.file_stem`.
- Produces:
  - `@dataclass CollectReport(saved: list[str], skipped: list[str], failed: dict[str, str])`
  - `gather_titles(client, categories: list[str]) -> list[str]`: unique titles, sorted.
  - `collect(client, categories: list[str], raw_dir: Path, log=print) -> CollectReport`: writes `raw_dir/<file_stem(requested title)>.json` holding the `RawPage` fields.

- [ ] **Step 1: Write the failing tests `tests/test_collector.py`**

```python
import json

from game_rag.collector import collect, gather_titles
from game_rag.titles import file_stem, page_url
from game_rag.wiki_client import RawPage, WikiError

MEMBERS = {"Lore": ["Owl", "Ashina"], "Characters": ["Owl", "Emma"]}
CATEGORIES = ["Lore", "Characters"]


def quiet(message):
    pass


class FakeClient:
    """Stands in for WikiClient so tests never touch the internet."""

    def __init__(self, members, broken=()):
        self.members = members
        self.broken = set(broken)
        self.page_requests = []

    def get_category_members(self, category):
        return self.members[category]

    def get_page(self, title):
        self.page_requests.append(title)
        if title in self.broken:
            raise WikiError("gave up after 3 attempts: HTTP 503")
        return RawPage(requested_title=title, title=title, url=page_url(title),
                       html=f"<p>{title} text</p>", categories=["Characters"])


def test_gather_titles_lists_each_page_once_sorted():
    assert gather_titles(FakeClient(MEMBERS), CATEGORIES) == ["Ashina", "Emma", "Owl"]


def test_collect_saves_one_json_file_per_page(tmp_path):
    report = collect(FakeClient(MEMBERS), CATEGORIES, tmp_path, log=quiet)
    assert report.saved == ["Ashina", "Emma", "Owl"]
    saved = json.loads((tmp_path / f"{file_stem('Owl')}.json").read_text(encoding="utf-8"))
    assert saved["title"] == "Owl"
    assert saved["url"] == page_url("Owl")
    assert saved["html"] == "<p>Owl text</p>"
    assert len(list(tmp_path.glob("*.json"))) == 3


def test_collect_resumes_without_downloading_twice(tmp_path):
    client = FakeClient(MEMBERS)
    collect(client, CATEGORIES, tmp_path, log=quiet)
    second = collect(client, CATEGORIES, tmp_path, log=quiet)
    assert second.saved == []
    assert second.skipped == ["Ashina", "Emma", "Owl"]
    assert client.page_requests == ["Ashina", "Emma", "Owl"]


def test_collect_records_failures_and_keeps_going(tmp_path):
    report = collect(FakeClient(MEMBERS, broken={"Emma"}), CATEGORIES, tmp_path, log=quiet)
    assert report.saved == ["Ashina", "Owl"]
    assert report.failed == {"Emma": "gave up after 3 attempts: HTTP 503"}
    assert not list(tmp_path.glob("*.tmp"))
```

- [ ] **Step 2: Run the tests and check they fail**

Run: `uv run pytest tests/test_collector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game_rag.collector'`

- [ ] **Step 3: Create `src/game_rag/collector.py`**

```python
"""Collector: download every lore page and save a raw copy (spec 3.1, part 1)."""
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from game_rag.titles import file_stem
from game_rag.wiki_client import WikiError


@dataclass
class CollectReport:
    saved: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


def gather_titles(client, categories: list[str]) -> list[str]:
    """Every page title in the given categories, each listed once, sorted."""
    titles = set()
    for category in categories:
        titles.update(client.get_category_members(category))
    return sorted(titles)


def collect(client, categories: list[str], raw_dir: Path, log=print) -> CollectReport:
    """Download pages that aren't saved yet. Safe to re-run: saved pages are skipped."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    report = CollectReport()
    titles = gather_titles(client, categories)
    log(f"Found {len(titles)} unique pages in {len(categories)} categories.")
    for number, title in enumerate(titles, start=1):
        path = raw_dir / f"{file_stem(title)}.json"
        if path.exists():
            report.skipped.append(title)
            continue
        try:
            page = client.get_page(title)
        except WikiError as err:
            report.failed[title] = str(err)
            log(f"[{number}/{len(titles)}] FAILED {title}: {err}")
            continue
        # Write to a temporary file first, so an interruption never leaves a half-written page.
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(page), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
        report.saved.append(title)
        log(f"[{number}/{len(titles)}] saved {title}")
    return report
```

- [ ] **Step 4: Run the tests and check they pass**

Run: `uv run pytest tests/test_collector.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit (owner)**

```bash
git add src/game_rag/collector.py tests/test_collector.py
git commit -m "feat: add resumable collector for lore pages"
git push
```

---

### Task 4: Cleaner

*Why:* raw wiki HTML is full of menus, images, edit links, and non-lore sections. The Cleaner keeps only the real text, split into sections under their headings (spec 3.1 part 2 and 4.1).

**Files:**
- Create: `src/game_rag/cleaner.py`, `tests/test_cleaner.py`

**Interfaces:**
- Consumes: `config.DROPPED_SECTIONS`.
- Produces:
  - `@dataclass Section(heading: str, level: int, text: str)`: `level` is 1 for the "Introduction" (text before the first heading) and 2–6 for real headings.
  - `@dataclass CleanPage(title: str, url: str, categories: list[str], sections: list[Section])`
  - `clean_html(html: str, dropped_sections=config.DROPPED_SECTIONS) -> list[Section]`
  - `clean_page(raw: dict) -> CleanPage`: `raw` has the keys of `RawPage`.

- [ ] **Step 1: Write the failing tests `tests/test_cleaner.py`**

```python
from game_rag.cleaner import CleanPage, Section, clean_html, clean_page

# Shaped like the real "Rot Essence" page (checked 2026-09-12).
ITEM_HTML = """
<div class="mw-content-ltr mw-parser-output">
<table class="article-table mw-collapsible"><tbody>
<tr><th colspan="4"><a href="/wiki/Items">Items</a></th></tr>
<tr><td><figure><img alt="Memory"/></figure><center><a href="/wiki/Memories">Memories</a></center></td></tr>
</tbody></table>
<h2><span class="mw-headline" id="In-Game_Description">In-Game Description</span><span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a>Sign in to edit</a><span class="mw-editsection-bracket">]</span></span></h2>
<p>The more one with the power of the Dragon's Heritage dies,<br>the more the sickness spreads.</p>
<h2><span class="mw-headline" id="Overview">Overview</span></h2>
<p><b>Dragonrot</b> is the name of the illness that has gripped <a href="/wiki/Ashina">Ashina</a>.</p>
<ul><li>It spreads after <a href="/wiki/Wolf">Wolf</a> dies.</li><li>It does <b>NOT</b> kill any NPC.</li></ul>
<table class="article-table mw-collapsible mw-collapsed"><tbody>
<tr><th>Event</th><th>Dialogue</th></tr>
<tr><td>Talking after first resurrection</td><td><u><b>Emma</b></u>: Hmm... Notice anything different?<br><u><b>Wolf</b></u>: ... Yes.</td></tr>
</tbody></table>
<h2><span class="mw-headline" id="Trivia">Trivia</span></h2>
<p>A trivia fact that should be dropped.</p>
<h3><span class="mw-headline" id="More">More trivia</span></h3>
<p>Also dropped.</p>
<h2><span class="mw-headline" id="Notes">Notes</span></h2>
<p>A note that should be kept.</p>
</div>
"""

# Shaped like the real "Owl" page, plus a newer-style heading and a tab box.
CHARACTER_HTML = """
<div class="mw-parser-output">
<table><tr><td><b>Owl</b></td><td>•</td><td><a>Owl (Father)</a></td></tr></table>
<div class="fluid hidden"><figure><img alt="Spacer"/></figure></div>
<p>Owl is a great shinobi.</p>
<div class="mw-heading mw-heading2"><h2 id="Description">Description</h2></div>
<aside class="portable-infobox"><h2 class="pi-title">Owl</h2><div>Voice actor: someone</div></aside>
<p>He raised Wolf.</p>
<div class="wikia-gallery"><div class="wikia-gallery-caption">Owl artwork</div></div>
<div class="tabber wds-tabber"><div class="wds-tabs__wrapper"><ul><li>Tab label</li></ul></div>
<div class="wds-tab__content"><p>Inside the tab.</p></div></div>
</div>
"""


def sections_by_heading(html):
    return {section.heading: section for section in clean_html(html)}


def test_keeps_only_real_sections_in_order():
    assert [s.heading for s in clean_html(ITEM_HTML)] == ["In-Game Description", "Overview", "Notes"]


def test_line_breaks_become_new_lines():
    text = sections_by_heading(ITEM_HTML)["In-Game Description"].text
    assert text == "The more one with the power of the Dragon's Heritage dies,\nthe more the sickness spreads."


def test_links_and_bold_become_plain_text():
    text = sections_by_heading(ITEM_HTML)["Overview"].text
    assert "Dragonrot is the name of the illness that has gripped Ashina." in text


def test_lists_become_dash_lines():
    text = sections_by_heading(ITEM_HTML)["Overview"].text
    assert "- It spreads after Wolf dies.\n- It does NOT kill any NPC." in text


def test_tables_become_rows():
    text = sections_by_heading(ITEM_HTML)["Overview"].text
    assert "Event | Dialogue" in text
    assert "Talking after first resurrection | Emma: Hmm... Notice anything different?\nWolf: ... Yes." in text


def test_dropped_sections_and_their_subsections_are_skipped():
    all_text = "\n".join(s.text for s in clean_html(ITEM_HTML))
    assert "trivia" not in all_text.lower()
    assert "Also dropped." not in all_text
    assert sections_by_heading(ITEM_HTML)["Notes"].text == "A note that should be kept."


def test_intro_paragraph_kept_and_navigation_dropped():
    first = clean_html(CHARACTER_HTML)[0]
    assert first == Section(heading="Introduction", level=1, text="Owl is a great shinobi.")


def test_new_style_heading_wrapper_is_recognised():
    second = clean_html(CHARACTER_HTML)[1]
    assert (second.heading, second.level) == ("Description", 2)


def test_infobox_gallery_and_tab_labels_are_removed():
    text = clean_html(CHARACTER_HTML)[1].text
    assert text == "He raised Wolf.\nInside the tab."


def test_strategy_sections_are_dropped():
    html = "<h2>Strategy</h2><p>Dodge left.</p><h2>Lore</h2><p>An old tale.</p>"
    assert clean_html(html) == [Section(heading="Lore", level=2, text="An old tale.")]


def test_clean_page_keeps_title_url_and_categories():
    raw = {
        "requested_title": "Dragonrot",
        "title": "Rot Essence",
        "url": "https://sekiro-shadows-die-twice.fandom.com/wiki/Rot_Essence",
        "html": "<h2>Overview</h2><p>Dragonrot spreads.</p>",
        "categories": ["Key Items"],
    }
    assert clean_page(raw) == CleanPage(
        title="Rot Essence",
        url="https://sekiro-shadows-die-twice.fandom.com/wiki/Rot_Essence",
        categories=["Key Items"],
        sections=[Section(heading="Overview", level=2, text="Dragonrot spreads.")],
    )
```

- [ ] **Step 2: Run the tests and check they fail**

Run: `uv run pytest tests/test_cleaner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game_rag.cleaner'`

- [ ] **Step 3: Create `src/game_rag/cleaner.py`**

```python
"""Cleaner: turn a wiki page's HTML into plain-text sections (spec 3.1, part 2)."""
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from game_rag import config

HEADING_LEVELS = {"h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
INTRO_HEADING = "Introduction"

# Page parts that are never lore: images, info boxes, edit links, galleries, tab labels, menus.
JUNK_SELECTORS = [
    "script", "style", "noscript", "figure", "img", "svg",
    "aside.portable-infobox", ".mw-editsection", ".navbox", ".wikia-gallery",
    ".thumb", ".toc", "#toc", "sup.reference", ".references",
    ".wds-tabs__wrapper", "div.fluid.hidden",
]


@dataclass
class Section:
    heading: str
    level: int
    text: str


@dataclass
class CleanPage:
    title: str
    url: str
    categories: list[str]
    sections: list[Section]


def clean_page(raw: dict) -> CleanPage:
    """Clean one raw page (a dict with the RawPage fields)."""
    return CleanPage(
        title=raw["title"],
        url=raw["url"],
        categories=raw["categories"],
        sections=clean_html(raw["html"]),
    )


def clean_html(html: str, dropped_sections=config.DROPPED_SECTIONS) -> list[Section]:
    """Split a page into sections of plain text, leaving out junk and dropped sections."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("div.mw-parser-output") or soup
    for selector in JUNK_SELECTORS:
        for element in root.select(selector):
            element.decompose()

    sections: list[Section] = []
    heading, level, parts = INTRO_HEADING, 1, []
    keeping = True
    dropped_level = None  # level of the heading being dropped; its subsections go too

    for child in root.children:
        if not isinstance(child, Tag):
            continue
        found = _heading_of(child)
        if found is not None:
            _finish(sections, heading, level, parts, keeping)
            new_level, new_heading = found
            if dropped_level is not None and new_level > dropped_level:
                keeping = False
            else:
                dropped_level = new_level if new_heading.lower() in dropped_sections else None
                keeping = dropped_level is None
            heading, level, parts = new_heading, new_level, []
            continue
        if not keeping:
            continue
        if level == 1 and child.name != "p":
            continue  # before the first heading only paragraphs are real text; the rest is navigation
        text = _element_text(child)
        if text:
            parts.append(text)

    _finish(sections, heading, level, parts, keeping)
    return sections


def _finish(sections, heading, level, parts, keeping):
    if keeping and parts:
        sections.append(Section(heading=heading, level=level, text="\n".join(parts)))


def _heading_of(element: Tag):
    """Return (level, heading text) if the element is a heading, else None."""
    if element.name in HEADING_LEVELS:
        return HEADING_LEVELS[element.name], _normalize(element.get_text(" "))
    if element.name == "div" and "mw-heading" in (element.get("class") or []):
        inner = element.find(list(HEADING_LEVELS))
        if inner is not None:
            return HEADING_LEVELS[inner.name], _normalize(inner.get_text(" "))
    return None


def _element_text(element: Tag) -> str:
    if element.name == "table":
        return _table_text(element)
    if element.name in ("ul", "ol"):
        items = (_inline_text(item) for item in element.find_all("li", recursive=False))
        return "\n".join(f"- {item}" for item in items if item)
    if element.name == "div":
        parts = []
        for child in element.children:
            if isinstance(child, Tag):
                parts.append(_element_text(child))
            elif isinstance(child, NavigableString) and not isinstance(child, Comment):
                parts.append(_normalize(str(child)))
        return "\n".join(part for part in parts if part)
    return _inline_text(element)


def _table_text(table: Tag) -> str:
    rows = []
    for row in table.find_all("tr"):
        cells = [_inline_text(cell) for cell in row.find_all(["th", "td"], recursive=False)]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _inline_text(element: Tag) -> str:
    for line_break in element.find_all("br"):
        line_break.replace_with("\n")
    return _normalize(element.get_text(""))


def _normalize(text: str) -> str:
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)
```

- [ ] **Step 4: Run the tests and check they pass**

Run: `uv run pytest tests/test_cleaner.py -v`
Expected: `11 passed`

- [ ] **Step 5: Commit (owner)**

```bash
git add src/game_rag/cleaner.py tests/test_cleaner.py
git commit -m "feat: add cleaner that turns wiki HTML into text sections"
git push
```

---

### Task 5: Clean the whole folder, measure, and the command-line tool

*Why:* ties the parts together so one command runs each step, and produces the numbers that later levels depend on (spec 4.2 step 2).

**Files:**
- Modify: `src/game_rag/cleaner.py` (add `CleanReport` and `clean_all`)
- Create: `src/game_rag/measure.py`, `src/game_rag/cli.py`, `src/game_rag/__main__.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `collect`, `WikiClient`, `clean_page`, `titles.file_stem`, `titles.page_url`, `config.*`.
- Produces:
  - `@dataclass CleanReport(written: list[str], duplicates: list[str], empty: list[str])`
  - `clean_all(raw_dir: Path, clean_dir: Path) -> CleanReport`: writes `clean_dir/<file_stem(final title)>.json` holding the `CleanPage` fields (sections as dicts with `heading`, `level`, `text`).
  - `measure.word_count(page: dict) -> int`
  - `measure.measure(clean_dir: Path) -> dict` with keys `pages`, `sections`, `total_words`, `average_words_per_page`, `median_words_per_page`, `largest_pages`, `smallest_pages`, `pages_per_category`.
  - `cli.main(argv: list[str] | None = None) -> int` with commands `collect`, `clean`, `stats`, `show <title>`.

- [ ] **Step 1: Write the failing tests `tests/test_pipeline.py`**

```python
import json

from game_rag import config
from game_rag.cleaner import clean_all
from game_rag.cli import main
from game_rag.measure import measure
from game_rag.titles import file_stem, page_url


def write_raw(raw_dir, requested, title, html):
    data = {"requested_title": requested, "title": title, "url": page_url(title),
            "html": html, "categories": ["Key Items"]}
    (raw_dir / f"{file_stem(requested)}.json").write_text(json.dumps(data), encoding="utf-8")


def write_clean(clean_dir, title, texts, categories):
    page = {"title": title, "url": page_url(title), "categories": categories,
            "sections": [{"heading": f"Part {i}", "level": 2, "text": t} for i, t in enumerate(texts)]}
    (clean_dir / f"{file_stem(title)}.json").write_text(json.dumps(page), encoding="utf-8")


def test_clean_all_skips_redirect_duplicates_and_empty_pages(tmp_path):
    raw, clean = tmp_path / "raw", tmp_path / "clean"
    raw.mkdir()
    write_raw(raw, "Rot Essence", "Rot Essence", "<h2>Overview</h2><p>Dragonrot spreads.</p>")
    write_raw(raw, "Dragonrot", "Rot Essence", "<h2>Overview</h2><p>Dragonrot spreads.</p>")
    write_raw(raw, "Stub", "Stub", "<table><tr><td>navigation only</td></tr></table>")
    report = clean_all(raw, clean)
    assert report.written == ["Rot Essence"]
    assert len(report.duplicates) == 1
    assert report.empty == ["Stub"]
    files = list(clean.glob("*.json"))
    assert len(files) == 1
    page = json.loads(files[0].read_text(encoding="utf-8"))
    assert page["sections"] == [{"heading": "Overview", "level": 2, "text": "Dragonrot spreads."}]


def test_measure_counts_pages_sections_and_words(tmp_path):
    write_clean(tmp_path, "Owl", ["one two three", "four five"], ["Characters"])
    write_clean(tmp_path, "Emma", ["one"], ["Characters", "Dialogues"])
    stats = measure(tmp_path)
    assert stats["pages"] == 2
    assert stats["sections"] == 3
    assert stats["total_words"] == 6
    assert stats["average_words_per_page"] == 3
    assert stats["median_words_per_page"] == 3
    assert stats["largest_pages"][0] == {"title": "Owl", "words": 5}
    assert stats["smallest_pages"][0] == {"title": "Emma", "words": 1}
    assert stats["pages_per_category"] == {"Characters": 2, "Dialogues": 1}


def test_measure_handles_an_empty_folder(tmp_path):
    stats = measure(tmp_path)
    assert stats["pages"] == 0
    assert stats["total_words"] == 0


def test_show_prints_a_clean_page(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "CLEAN_DIR", tmp_path)
    write_clean(tmp_path, "Owl", ["Owl is a great shinobi."], ["Characters"])
    assert main(["show", "Owl"]) == 0
    out = capsys.readouterr().out
    assert "## Part 0" in out
    assert "Owl is a great shinobi." in out


def test_show_reports_a_missing_page(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "CLEAN_DIR", tmp_path)
    assert main(["show", "Nobody"]) == 1
    assert "not found" in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests and check they fail**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL with `ImportError: cannot import name 'clean_all' from 'game_rag.cleaner'`

- [ ] **Step 3: Add `clean_all` to `src/game_rag/cleaner.py`**

Change the import block at the top of the file to:

```python
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from game_rag import config
from game_rag.titles import file_stem
```

Then add below `clean_page`:

```python
@dataclass
class CleanReport:
    written: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)


def clean_all(raw_dir: Path, clean_dir: Path) -> CleanReport:
    """Clean every raw page. Redirects to an already-cleaned page are skipped."""
    clean_dir.mkdir(parents=True, exist_ok=True)
    report = CleanReport()
    seen = set()
    for raw_path in sorted(raw_dir.glob("*.json")):
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        page = clean_page(raw)
        if page.title in seen:
            report.duplicates.append(raw["requested_title"])
            continue
        seen.add(page.title)
        if not page.sections:
            report.empty.append(page.title)
            continue
        out_path = clean_dir / f"{file_stem(page.title)}.json"
        out_path.write_text(json.dumps(asdict(page), ensure_ascii=False, indent=2), encoding="utf-8")
        report.written.append(page.title)
    return report
```

- [ ] **Step 4: Create `src/game_rag/measure.py`**

```python
"""Measure the clean data: how many pages, sections, and words (spec 4.2, step 2)."""
import json
import statistics
from collections import Counter
from pathlib import Path


def word_count(page: dict) -> int:
    return sum(len(section["text"].split()) for section in page["sections"])


def measure(clean_dir: Path) -> dict:
    pages = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(clean_dir.glob("*.json"))]
    sizes = sorted(({"title": p["title"], "words": word_count(p)} for p in pages),
                   key=lambda size: size["words"], reverse=True)
    words = [size["words"] for size in sizes]
    categories = Counter(category for p in pages for category in p["categories"])
    return {
        "pages": len(pages),
        "sections": sum(len(p["sections"]) for p in pages),
        "total_words": sum(words),
        "average_words_per_page": round(sum(words) / len(words)) if words else 0,
        "median_words_per_page": round(statistics.median(words)) if words else 0,
        "largest_pages": sizes[:10],
        "smallest_pages": sizes[::-1][:10],
        "pages_per_category": dict(categories.most_common()),
    }
```

- [ ] **Step 5: Create `src/game_rag/cli.py`**

```python
"""Command-line tool: uv run python -m game_rag <collect|clean|stats|show>"""
import argparse
import json
import sys

from game_rag import config
from game_rag.cleaner import clean_all
from game_rag.collector import collect
from game_rag.measure import measure
from game_rag.titles import file_stem
from game_rag.wiki_client import WikiClient


def main(argv: list[str] | None = None) -> int:
    _use_utf8_output()
    parser = argparse.ArgumentParser(prog="game_rag", description="game_rag data tools")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("collect", help="download lore pages from the wiki (safe to re-run)")
    commands.add_parser("clean", help="turn raw pages into clean text sections")
    commands.add_parser("stats", help="count pages and words, save data/stats.json")
    show = commands.add_parser("show", help="print one clean page")
    show.add_argument("title", help='exact page title, e.g. "Rot Essence"')
    args = parser.parse_args(argv)

    if args.command == "collect":
        return _collect()
    if args.command == "clean":
        return _clean()
    if args.command == "stats":
        return _stats()
    return _show(args.title)


def _collect() -> int:
    report = collect(WikiClient(), config.LORE_CATEGORIES, config.RAW_DIR)
    print(f"\nDone. Saved {len(report.saved)}, already had {len(report.skipped)}, failed {len(report.failed)}.")
    for title, problem in report.failed.items():
        print(f"  FAILED: {title} -> {problem}")
    if report.failed:
        print("Run the same command again to retry the failed pages.")
        return 1
    return 0


def _clean() -> int:
    report = clean_all(config.RAW_DIR, config.CLEAN_DIR)
    if not report.written:
        print("Nothing to clean. Run `uv run python -m game_rag collect` first.")
        return 1
    print(f"Wrote {len(report.written)} clean pages to {config.CLEAN_DIR}")
    print(f"Skipped {len(report.duplicates)} duplicates (redirects) and {len(report.empty)} empty pages.")
    for title in report.empty:
        print(f"  empty: {title}")
    return 0


def _stats() -> int:
    stats = measure(config.CLEAN_DIR)
    config.STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.STATS_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pages:            {stats['pages']}")
    print(f"Sections:         {stats['sections']}")
    print(f"Total words:      {stats['total_words']}")
    print(f"Average per page: {stats['average_words_per_page']} words")
    print(f"Median per page:  {stats['median_words_per_page']} words")
    print("Largest pages:")
    for size in stats["largest_pages"]:
        print(f"  {size['words']:>6}  {size['title']}")
    print(f"Saved to {config.STATS_FILE}")
    return 0


def _show(title: str) -> int:
    path = config.CLEAN_DIR / f"{file_stem(title)}.json"
    if not path.exists():
        print(f'"{title}" not found. Titles are exact and case-sensitive; look in {config.CLEAN_DIR}.')
        return 1
    page = json.loads(path.read_text(encoding="utf-8"))
    print(f"{page['title']}  ({page['url']})")
    print(f"Categories: {', '.join(page['categories'])}\n")
    for section in page["sections"]:
        print(f"{'#' * section['level']} {section['heading']}")
        print(section["text"] + "\n")
    return 0


def _use_utf8_output() -> None:
    """Some pages contain Japanese text; make sure the Windows console can print it."""
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "")
    if encoding != "utf8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
```

- [ ] **Step 6: Create `src/game_rag/__main__.py`**

```python
from game_rag.cli import main

raise SystemExit(main())
```

- [ ] **Step 7: Run the new tests and check they pass**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: `5 passed`

- [ ] **Step 8: Run the whole test suite**

Run: `uv run pytest -v`
Expected: `32 passed`

- [ ] **Step 9: Commit (owner)**

```bash
git add src tests
git commit -m "feat: add clean_all, measurements, and command-line tool"
git push
```

---

### Task 6: Run it for real and look at the data

*Why:* spec Level 0 "done when": clean Sekiro lore pages are on disk and their size is recorded. This is also the lesson: **always look at real data before building on it.**

**Files:**
- Create (by commands): `data/raw/*.json` (not committed), `data/clean/*.json`, `data/stats.json`
- Create (by hand): `data/README.md`, `docs/level-0-notes.md`

- [ ] **Step 1: Download the pages** (about 6–8 minutes; leave it running)

Run: `uv run python -m game_rag collect`
Expected: starts with `Found 276 unique pages in 10 categories.` (the number may differ slightly if the wiki changed), prints one line per page, and ends with `Done. Saved 276, already had 0, failed 0.` If it stops or some pages fail, run the same command again; it only downloads what's missing.

- [ ] **Step 2: Clean them**

Run: `uv run python -m game_rag clean`
Expected: `Wrote N clean pages to ...\data\clean` with N close to 276, plus a list of any empty pages.

- [ ] **Step 3: Measure them**

Run: `uv run python -m game_rag stats`
Expected: page, section, and word counts, the 10 largest pages, and `Saved to ...\data\stats.json`.

- [ ] **Step 4: Look at three pages yourself**

```bash
uv run python -m game_rag show "Rot Essence"
```

```bash
uv run python -m game_rag show "Great Shinobi - Owl"
```

```bash
uv run python -m game_rag show "Ending 1: Shura"
```

Check each against this list:
- No leftover junk: `Sign in to edit`, `[ ]`, image file names, or rows of navigation links.
- The In-Game Description and the dialogue lines survived.
- Trivia and strategy sections are gone.
- Headings match the real wiki page (open the URL printed at the top to compare).

If you spot junk, that's the lesson working. Find its HTML class in the raw file (`data/raw/<name>.json`), add a test to `tests/test_cleaner.py` that reproduces it, add the class to `JUNK_SELECTORS` in `src/game_rag/cleaner.py`, run `uv run pytest`, then repeat Steps 2–4.

- [ ] **Step 5: Credit the data: create `data/README.md`**

```markdown
# Data

- `raw/`: raw page downloads. Not committed; recreate with `uv run python -m game_rag collect`.
- `clean/`: cleaned text of Sekiro lore pages, one JSON file per page.
- `stats.json`: page and word counts from `uv run python -m game_rag stats`.

The wiki text in this folder comes from the [Sekiro: Shadows Die Twice Fandom wiki](https://sekiro-shadows-die-twice.fandom.com/) and its contributors. It is licensed [CC BY-SA](https://www.fandom.com/licensing) and shared here under the same license. Every page keeps a link to its source.

Unofficial fan project. Not affiliated with FromSoftware or Activision.
```

- [ ] **Step 6: Write your observations in `docs/level-0-notes.md`**

Copy the numbers from `data/stats.json` and write down what you noticed:

```markdown
# Level 0 notes

## Numbers (from data/stats.json)
- Pages:
- Sections:
- Total words:
- Average / median words per page:
- Largest page:

## Where the data came from
- Special:Statistics (database download) is behind a bot check, so pages were fetched through the public API at about 1 page per second.

## What I noticed when reading pages
1.
2.
3.

## Questions for Level 1
-
```

- [ ] **Step 7: Run the full test suite one last time**

Run: `uv run pytest`
Expected: all tests pass (32, plus any you added in Step 4).

- [ ] **Step 8: Commit (owner)**

```bash
git add data/clean data/stats.json data/README.md docs/level-0-notes.md
git commit -m "data: add cleaned Sekiro lore pages and Level 0 measurements"
git push
```

**Level 0 is done** when the pages are cleaned, `data/stats.json` exists, and your notes are written. The next plan (Level 1: naive RAG with Ollama) starts from these measurements.
