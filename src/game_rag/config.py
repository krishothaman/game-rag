from pathlib import Path

API_URL = "https://sekiro-shadows-die-twice.fandom.com/api.php"
USER_AGENT = "game_rag/0.1 (free open-source RAG learning project)"
REQUEST_DELAY_SECONDS = 1.1  # dont spam the wiki, max ~1 request a second

# categories that actually have lore. bosses are in now, the cleaner drops their strategy sections
LORE_CATEGORIES = [
    "Lore", "Characters", "Bosses", "Mini-Bosses", "Endings", "Key Items", "Prosthetic Tools",
    "Memories", "Locations", "Chapters", "Dialogue", "Dialogues",
]

# sections we throw away. either not lore (strategy, loot, shops) or not canon (cut content)
DROPPED_SECTIONS = {
    "trivia", "speculation", "strategy", "strategies", "walkthrough", "fight", "new game plus",
    "availability", "loot", "wares", "trophy", "cut content", "cut dialogue", "cut dialogues",
    "gallery", "video", "videos", "references",
}

# boss strategy headings get named a million ways ("Behaviors and Tactics", "Phase 1 & 2"...)
# so any heading with one of these in it goes too
DROPPED_KEYWORDS = ["tactic", "moveset", "equipment", "phase", "preparation", "stealth route", "strateg"]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
STATS_FILE = PROJECT_ROOT / "data" / "stats.json"

# level 1 rag settings
GAME = "Sekiro"
CHAT_MODEL = "qwen3.5:4b"
EMBED_MODEL = "qwen3-embedding:0.6b"
# qwen3-embedding wants questions to come with a little instruction in front, documents go in plain
QUERY_INSTRUCTION = "Instruct: Given a question about Sekiro lore, retrieve wiki passages that answer it\nQuery: "
CHUNK_WORDS = 300
CHUNK_OVERLAP = 50
TOP_K = 5
LIBRARY_DIR = PROJECT_ROOT / "data" / "library"
COLLECTION = "sekiro"
GOLDEN_FILE = PROJECT_ROOT / "data" / "golden" / "sekiro.jsonl"
VERDICTS_FILE = PROJECT_ROOT / "data" / "golden" / "sekiro-verdicts.json"
# locked questions we never tune against, only scored at the end of a level
HOLDOUT_FILE = PROJECT_ROOT / "data" / "golden" / "holdout.jsonl"
HOLDOUT_VERDICTS_FILE = PROJECT_ROOT / "data" / "golden" / "holdout-verdicts.json"
