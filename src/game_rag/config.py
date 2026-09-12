from pathlib import Path

API_URL = "https://sekiro-shadows-die-twice.fandom.com/api.php"
USER_AGENT = "game_rag/0.1 (free open-source RAG learning project)"
REQUEST_DELAY_SECONDS = 1.1  # dont spam the wiki, max ~1 request a second

# categories that actually have lore. skipped bosses bc those pages are mostly strategy
LORE_CATEGORIES = [
    "Lore", "Characters", "Endings", "Key Items", "Prosthetic Tools",
    "Memories", "Locations", "Chapters", "Dialogue", "Dialogues",
]

# sections we throw away, not lore
DROPPED_SECTIONS = {
    "trivia", "speculation", "strategy", "strategies", "walkthrough",
    "gallery", "video", "videos", "references",
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
STATS_FILE = PROJECT_ROOT / "data" / "stats.json"
