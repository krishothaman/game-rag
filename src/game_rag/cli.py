import argparse
import json
import sys
import time

import ollama

from game_rag import config
from game_rag.answerer import Answerer, cited_numbers
from game_rag.chunker import chunk_all
from game_rag.cleaner import clean_all
from game_rag.collector import collect
from game_rag.embedder import Embedder
from game_rag.golden import load_golden, pages_found
from game_rag.library import Library
from game_rag.measure import measure
from game_rag.titles import file_stem
from game_rag.wiki_client import WikiClient


def main(argv=None):
    use_utf8_output()
    parser = argparse.ArgumentParser(prog="game_rag", description="ask questions about game lore, answered from the wiki")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("collect", help="download lore pages from the wiki (safe to re-run)")
    commands.add_parser("clean", help="turn raw pages into clean text sections")
    commands.add_parser("stats", help="count pages and words, save data/stats.json")
    show = commands.add_parser("show", help="print one clean page")
    show.add_argument("title", help='exact page title, e.g. "Rot Essence"')
    commands.add_parser("index", help="chunk + embed the clean pages into the library")
    ask = commands.add_parser("ask", help="ask one question")
    ask.add_argument("question")
    ask.add_argument("--debug", action="store_true", help="show the chunks that were found")
    chat = commands.add_parser("chat", help="keep asking questions until you type exit")
    chat.add_argument("--debug", action="store_true", help="show the chunks that were found")
    commands.add_parser("score", help="run the golden questions and score the rag")
    args = parser.parse_args(argv)

    try:
        if args.command == "collect":
            return run_collect()
        if args.command == "clean":
            return run_clean()
        if args.command == "stats":
            return run_stats()
        if args.command == "index":
            return run_index()
        if args.command == "ask":
            return run_ask(args.question, args.debug)
        if args.command == "chat":
            return run_chat(args.debug)
        if args.command == "score":
            return run_score()
        return run_show(args.title)
    except ConnectionError:
        print("Can't reach Ollama. Open the Ollama app (or run `ollama serve`) and try again.")
        return 1
    except ollama.ResponseError as e:
        print(f"Ollama said: {e.error}")
        if e.status_code == 404:
            print(f"Missing a model? Run: ollama pull {config.CHAT_MODEL}  and  ollama pull {config.EMBED_MODEL}")
        return 1


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


def make_library():
    return Library(Embedder())


def make_answerer():
    return Answerer()


def run_index():
    chunks = chunk_all(config.CLEAN_DIR)
    if not chunks:
        print("No clean pages. Run `uv run python -m game_rag clean` first.")
        return 1
    print(f"Cut {len(chunks)} chunks from the clean pages. Embedding them now...")
    started = time.time()
    make_library().rebuild(chunks)
    print(f"Library ready in {time.time() - started:.0f}s at {config.LIBRARY_DIR}")
    return 0


def run_ask(question, debug):
    library = make_library()
    if library.count() == 0:
        print("The library is empty. Run `uv run python -m game_rag index` first.")
        return 1
    return answer_question(question, library, make_answerer(), debug)


def run_chat(debug):
    library = make_library()
    if library.count() == 0:
        print("The library is empty. Run `uv run python -m game_rag index` first.")
        return 1
    answerer = make_answerer()
    print("Ask about Sekiro lore. Type exit to quit.\n")
    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question.lower() in ("", "exit", "quit"):
            return 0
        answer_question(question, library, answerer, debug)
        print()


def run_score():
    library = make_library()
    if library.count() == 0:
        print("The library is empty. Run `uv run python -m game_rag index` first.")
        return 1

    questions = [q for q in load_golden(config.GOLDEN_FILE) if not q.not_covered]
    found_count = 0
    for q in questions:
        hits = library.search(q.question)
        found = pages_found(q, hits)
        if found:
            found_count += 1
        label = "FOUND " if found else "MISSED"
        print(f"{label} #{q.id} {q.question}  ({len(found)}/{len(q.pages)} pages)")
        if not found:
            print(f"         wanted: {', '.join(q.pages)}")
            print(f"         got:    {', '.join(h.chunk.page_title for h in hits)}")

    print(f"\nRetrieval: {found_count}/{len(questions)} questions had a right page in the top {config.TOP_K}")
    return 0


def answer_question(question, library, answerer, debug=False):
    hits = library.search(question)
    if debug:
        print("--- chunks found ---")
        for i, h in enumerate(hits, start=1):
            print(f"[{i}] similarity {h.similarity:.2f}  {h.chunk.page_title} > {h.chunk.section}")
            print(f"    {h.chunk.text[:300]}{'...' if len(h.chunk.text) > 300 else ''}")
        print("--------------------\n")

    answer = answerer.answer(question, hits)
    print(answer)

    cited = cited_numbers(answer, len(hits))
    if cited:
        print("\nSources:")
        for n in cited:
            c = hits[n - 1].chunk
            print(f"  [{n}] {c.page_title} > {c.section}  {c.url}")
    return 0


def use_utf8_output():
    # some pages have japanese text in them, windows console chokes on it without this
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "")
    if encoding != "utf8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
