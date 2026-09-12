import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from game_rag import config

HEADINGS = {"h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

# stuff on wiki pages that's never lore - pics, infoboxes, edit links, galleries, tab buttons
JUNK = [
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


def clean_page(raw):
    return CleanPage(
        title=raw["title"],
        url=raw["url"],
        categories=raw["categories"],
        sections=clean_html(raw["html"]),
    )


def clean_html(html, dropped_sections=config.DROPPED_SECTIONS):
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("div.mw-parser-output") or soup
    for selector in JUNK:
        for el in root.select(selector):
            el.decompose()

    sections = []
    # text before the first heading goes in a fake "Introduction" section
    heading, level, parts = "Introduction", 1, []
    keeping = True
    dropped_level = None

    for child in root.children:
        if not isinstance(child, Tag):
            continue

        found = heading_of(child)
        if found:
            add_section(sections, heading, level, parts, keeping)
            new_level, new_heading = found
            # a subsection of something we're dropping (like h3 under Trivia) gets dropped too
            if dropped_level is not None and new_level > dropped_level:
                keeping = False
            else:
                dropped_level = new_level if new_heading.lower() in dropped_sections else None
                keeping = dropped_level is None
            heading, level, parts = new_heading, new_level, []
            continue

        if not keeping:
            continue
        # before the first heading its all nav menus, only real paragraphs are worth keeping
        if level == 1 and child.name != "p":
            continue
        text = element_text(child)
        if text:
            parts.append(text)

    add_section(sections, heading, level, parts, keeping)
    return sections


def add_section(sections, heading, level, parts, keeping):
    if keeping and parts:
        sections.append(Section(heading=heading, level=level, text="\n".join(parts)))


def heading_of(el):
    if el.name in HEADINGS:
        return HEADINGS[el.name], tidy(el.get_text(" "))
    # newer wiki pages wrap headings in a div
    if el.name == "div" and "mw-heading" in (el.get("class") or []):
        inner = el.find(list(HEADINGS))
        if inner is not None:
            return HEADINGS[inner.name], tidy(inner.get_text(" "))
    return None


def element_text(el):
    if el.name == "table":
        return table_text(el)
    if el.name in ("ul", "ol"):
        items = (inline_text(li) for li in el.find_all("li", recursive=False))
        return "\n".join(f"- {item}" for item in items if item)
    # divs (like tab boxes) can have tables and lists inside, so go through what's in them
    if el.name == "div":
        parts = []
        for child in el.children:
            if isinstance(child, Tag):
                parts.append(element_text(child))
            elif isinstance(child, NavigableString) and not isinstance(child, Comment):
                parts.append(tidy(str(child)))
        return "\n".join(p for p in parts if p)
    return inline_text(el)


def table_text(table):
    # each row becomes "cell | cell | cell"
    rows = []
    for tr in table.find_all("tr"):
        cells = [inline_text(cell) for cell in tr.find_all(["th", "td"], recursive=False)]
        cells = [c for c in cells if c]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def inline_text(el):
    for br in el.find_all("br"):
        br.replace_with("\n")
    return tidy(el.get_text(""))


def tidy(text):
    # squash extra spaces and throw away empty lines
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)
