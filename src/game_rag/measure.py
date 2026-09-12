import json
import statistics
from collections import Counter


def word_count(page):
    return sum(len(s["text"].split()) for s in page["sections"])


def measure(clean_dir):
    pages = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(clean_dir.glob("*.json"))]
    sizes = sorted(({"title": p["title"], "words": word_count(p)} for p in pages),
                   key=lambda s: s["words"], reverse=True)
    words = [s["words"] for s in sizes]
    categories = Counter(c for p in pages for c in p["categories"])
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
