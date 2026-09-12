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
