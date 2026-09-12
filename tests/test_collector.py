import json

from game_rag.collector import collect, gather_titles
from game_rag.titles import file_stem, page_url
from game_rag.wiki_client import RawPage, WikiError

MEMBERS = {"Lore": ["Owl", "Ashina"], "Characters": ["Owl", "Emma"]}
CATEGORIES = ["Lore", "Characters"]


def quiet(message):
    pass


# fake wiki client, hands back made up pages instead of downloading
class FakeClient:
    def __init__(self, members, broken=()):
        self.members = members
        self.broken = set(broken)
        self.page_requests = []

    def get_category_members(self, category):
        return self.members[category]

    def get_page(self, title):
        self.page_requests.append(title)
        if title in self.broken:
            raise WikiError("gave up after 3 attempts: HTTP 503")
        return RawPage(requested_title=title, title=title, url=page_url(title),
                       html=f"<p>{title} text</p>", categories=["Characters"])


def test_gather_titles_lists_each_page_once_sorted():
    assert gather_titles(FakeClient(MEMBERS), CATEGORIES) == ["Ashina", "Emma", "Owl"]


def test_collect_saves_one_json_file_per_page(tmp_path):
    report = collect(FakeClient(MEMBERS), CATEGORIES, tmp_path, log=quiet)
    assert report.saved == ["Ashina", "Emma", "Owl"]
    saved = json.loads((tmp_path / f"{file_stem('Owl')}.json").read_text(encoding="utf-8"))
    assert saved["title"] == "Owl"
    assert saved["url"] == page_url("Owl")
    assert saved["html"] == "<p>Owl text</p>"
    assert len(list(tmp_path.glob("*.json"))) == 3


def test_collect_resumes_without_downloading_twice(tmp_path):
    client = FakeClient(MEMBERS)
    collect(client, CATEGORIES, tmp_path, log=quiet)
    second = collect(client, CATEGORIES, tmp_path, log=quiet)
    assert second.saved == []
    assert second.skipped == ["Ashina", "Emma", "Owl"]
    assert client.page_requests == ["Ashina", "Emma", "Owl"]


def test_collect_records_failures_and_keeps_going(tmp_path):
    report = collect(FakeClient(MEMBERS, broken={"Emma"}), CATEGORIES, tmp_path, log=quiet)
    assert report.saved == ["Ashina", "Owl"]
    assert report.failed == {"Emma": "gave up after 3 attempts: HTTP 503"}
    assert not list(tmp_path.glob("*.tmp"))
