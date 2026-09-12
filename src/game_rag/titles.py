import hashlib
import re
from urllib.parse import quote

WIKI_BASE_URL = "https://sekiro-shadows-die-twice.fandom.com/wiki/"


def page_url(title):
    # "Great Shinobi - Owl" -> .../wiki/Great_Shinobi_-_Owl
    return WIKI_BASE_URL + quote(title.replace(" ", "_"), safe="/:()'-,._!")


def file_stem(title):
    # windows hates stuff like "/" in filenames so swap anything weird for _
    # hash on the end so "Emma/Dialogue" and "Emma Dialogue" dont overwrite each other
    readable = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_") or "page"
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"
