import argparse
import json
import sys

from game_rag import config
from game_rag.cleaner import clean_all
from game_rag.collector import collect
from game_rag.measure import measure
from game_rag.titles import file_stem
from game_rag.wiki_client import WikiClient


def main(argv=None):
    use_utf8_output()
    parser = argparse.ArgumentParser(prog="game_rag", description="game_rag data tools")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("collect", help="download lore pages from the wiki (safe to re-run)")
    commands.add_parser("clean", help="turn raw pages into clean text sections")
    commands.add_parser("stats", help="count pages and words, save data/stats.json")
    show = commands.add_parser("show", help="print one clean page")
    show.add_argument("title", help='exact page title, e.g. "Rot Essence"')
    args = parser.parse_args(argv)

    if args.command == "collect":
        return run_collect()
    if args.command == "clean":
        return run_clean()
    if args.command == "stats":
        return run_stats()
    return run_show(args.title)


def run_collect():
    report = collect(WikiClient(), config.LORE_CATEGORIES, config.RAW_DIR)
    print(f"\nDone. Saved {len(report.saved)}, already had {len(report.skipped)}, failed {len(report.failed)}.")
    for title, problem in report.failed.items():
        print(f"  FAILED: {title} -> {problem}")
    if report.failed:
        print("Run the same command again to retry the failed pages.")
        return 1
    return 0


def run_clean():
    report = clean_all(config.RAW_DIR, config.CLEAN_DIR)
    if not report.written:
        print("Nothing to clean. Run `uv run python -m game_rag collect` first.")
        return 1
    print(f"Wrote {len(report.written)} clean pages to {config.CLEAN_DIR}")
    print(f"Skipped {len(report.duplicates)} duplicates (redirects) and {len(report.empty)} empty pages.")
    for title in report.empty:
        print(f"  empty: {title}")
    return 0


def run_stats():
    stats = measure(config.CLEAN_DIR)
    config.STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.STATS_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pages:            {stats['pages']}")
    print(f"Sections:         {stats['sections']}")
    print(f"Total words:      {stats['total_words']}")
    print(f"Average per page: {stats['average_words_per_page']} words")
    print(f"Median per page:  {stats['median_words_per_page']} words")
    print("Largest pages:")
    for s in stats["largest_pages"]:
        print(f"  {s['words']:>6}  {s['title']}")
    print(f"Saved to {config.STATS_FILE}")
    return 0


def run_show(title):
    path = config.CLEAN_DIR / f"{file_stem(title)}.json"
    if not path.exists():
        print(f'"{title}" not found. Titles are exact and case-sensitive, check {config.CLEAN_DIR}')
        return 1
    page = json.loads(path.read_text(encoding="utf-8"))
    print(f"{page['title']}  ({page['url']})")
    print(f"Categories: {', '.join(page['categories'])}\n")
    for s in page["sections"]:
        print(f"{'#' * s['level']} {s['heading']}")
        print(s["text"] + "\n")
    return 0


def use_utf8_output():
    # some pages have japanese text in them, windows console chokes on it without this
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "")
    if encoding != "utf8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
