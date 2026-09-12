import json
from dataclasses import asdict, dataclass, field

from game_rag.titles import file_stem
from game_rag.wiki_client import WikiError


@dataclass
class CollectReport:
    saved: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


def gather_titles(client, categories):
    # set bc some pages are in more than one category (owl is in lore AND characters)
    titles = set()
    for category in categories:
        titles.update(client.get_category_members(category))
    return sorted(titles)


def collect(client, categories, raw_dir, log=print):
    raw_dir.mkdir(parents=True, exist_ok=True)
    report = CollectReport()
    titles = gather_titles(client, categories)
    log(f"Found {len(titles)} unique pages in {len(categories)} categories.")

    for i, title in enumerate(titles, start=1):
        path = raw_dir / f"{file_stem(title)}.json"
        # already got this one from a previous run, skip it
        if path.exists():
            report.skipped.append(title)
            continue
        try:
            page = client.get_page(title)
        except WikiError as e:
            report.failed[title] = str(e)
            log(f"[{i}/{len(titles)}] FAILED {title}: {e}")
            continue
        # write to .tmp first then rename, so a crash mid-write never leaves a half file behind
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(page), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        report.saved.append(title)
        log(f"[{i}/{len(titles)}] saved {title}")

    return report
