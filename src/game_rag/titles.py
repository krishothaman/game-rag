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
