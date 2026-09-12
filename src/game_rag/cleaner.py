import json
import re
from dataclasses import asdict, dataclass, field

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from game_rag import config
from game_rag.titles import file_stem

HEADINGS = {"h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

# stuff on wiki pages that's never lore - pics, infoboxes, edit links, galleries, tab buttons
JUNK = [
    "script", "style", "noscript", "figure", "img", "svg",
    "aside.portable-infobox", ".mw-editsection", ".navbox", ".wikia-gallery",
    ".thumb", ".toc", "#toc", "sup.reference", ".references",
    ".wds-tabs__wrapper", "div.fluid.hidden",
]

# menus are basically all links. real content (even dialogue tables) is way under this
NAV_LINK_SHARE = 0.5
# a one-cell top row shorter than this is a table title like "Dialogue", longer ones are quotes
TITLE_MAX_CHARS = 40


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


@dataclass
class CleanReport:
    written: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)


def clean_all(raw_dir, clean_dir):
    clean_dir.mkdir(parents=True, exist_ok=True)
    report = CleanReport()
    seen = set()
    for raw_path in sorted(raw_dir.glob("*.json")):
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        page = clean_page(raw)
        # two raw files can end up being the same page (redirects), keep just one
        if page.title in seen:
            report.duplicates.append(raw["requested_title"])
            continue
        seen.add(page.title)
        if not page.sections:
            report.empty.append(page.title)
            continue
        out = clean_dir / f"{file_stem(page.title)}.json"
        out.write_text(json.dumps(asdict(page), ensure_ascii=False, indent=2), encoding="utf-8")
        report.written.append(page.title)
    return report


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
        if child.name in ("table", "div") and is_navigation(child):
            continue

        found = heading_of(child) or pseudo_heading(child, dropped_sections)
        if found:
            add_section(sections, heading, level, parts, keeping)
            new_level, new_heading = found
            # a subsection of something we're dropping (like h3 under Trivia) gets dropped too
            if dropped_level is not None and new_level > dropped_level:
                keeping = False
            else:
                dropped_level = new_level if is_dropped(new_heading, dropped_sections) else None
                keeping = dropped_level is None
            heading, level, parts = new_heading, new_level, []
            # if the "heading" was a table's title row, the rest of that table goes in this section
            if keeping and child.name == "table":
                text = table_text(child, skip_title=True)
                if text:
                    parts.append(text)
            continue

        if keeping:
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


def is_dropped(heading, dropped_sections):
    h = heading.lower()
    # "Emma's Cut Dialogue" should go too, not just a plain "Cut Dialogue"
    if any(h == name or h.endswith(" " + name) for name in dropped_sections):
        return True
    return any(word in h for word in config.DROPPED_KEYWORDS)


def is_navigation(el):
    text = len(el.get_text("", strip=True))
    if text == 0:
        return True
    links = sum(len(a.get_text("", strip=True)) for a in el.select("a, .selflink"))
    return links / text >= NAV_LINK_SHARE


def pseudo_heading(el, dropped_sections):
    # tables with a one-cell title row like "Dialogue" or "Loot" work like headings
    if el.name == "table":
        title = table_title(el)
        if title:
            return 2, title
    # stray labels like "Gallery" sitting in a plain div
    if el.name == "div" and not el.get("class"):
        text = tidy(el.get_text(" "))
        if is_dropped(text, dropped_sections):
            return 2, text
    return None


def table_title(table):
    first = table.find("tr")
    if first is None:
        return None
    cells = first.find_all(["th", "td"], recursive=False)
    if len(cells) != 1:
        return None
    text = tidy(cells[0].get_text(" "))
    if text and len(text) <= TITLE_MAX_CHARS and "\n" not in text:
        return text
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


def table_text(table, skip_title=False):
    # each row becomes "cell | cell | cell"
    rows = []
    # only this table's own rows. a table inside a cell already gets read with that cell
    trs = [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]
    if skip_title:
        trs = trs[1:]
    for tr in trs:
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
