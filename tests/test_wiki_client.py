import pytest
import requests

from game_rag import config
from game_rag.wiki_client import WikiClient, WikiError


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


# pretends to be requests.Session so the tests dont touch the internet
class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_client(responses, sleeps=None):
    session = FakeSession(responses)
    recorded = sleeps if sleeps is not None else []
    client = WikiClient(session=session, delay_seconds=1.1, max_attempts=3, sleep=recorded.append)
    return client, session


PAGE_PAYLOAD = {
    "parse": {
        "title": "Rot Essence",
        "text": "<p>Dragonrot</p>",
        "categories": [{"category": "Key_Items"}, {"category": "Items"}],
    }
}


def test_sets_a_descriptive_user_agent():
    _, session = make_client([])
    assert session.headers["User-Agent"] == config.USER_AGENT


def test_category_members_follows_continue_tokens():
    first = FakeResponse(payload={
        "query": {"categorymembers": [{"title": "Ashina"}, {"title": "Owl"}]},
        "continue": {"cmcontinue": "page|X", "continue": "-||"},
    })
    second = FakeResponse(payload={"query": {"categorymembers": [{"title": "Emma"}]}})
    client, session = make_client([first, second])
    assert client.get_category_members("Characters") == ["Ashina", "Owl", "Emma"]
    assert session.calls[0]["cmtitle"] == "Category:Characters"
    assert session.calls[1]["cmcontinue"] == "page|X"


def test_get_page_follows_redirect_and_cleans_category_names():
    client, session = make_client([FakeResponse(payload=PAGE_PAYLOAD)])
    page = client.get_page("Dragonrot")
    assert page.requested_title == "Dragonrot"
    assert page.title == "Rot Essence"
    assert page.url == "https://sekiro-shadows-die-twice.fandom.com/wiki/Rot_Essence"
    assert page.html == "<p>Dragonrot</p>"
    assert page.categories == ["Key Items", "Items"]
    assert session.calls[0]["redirects"] == "1"


def test_waits_before_every_request():
    sleeps = []
    client, _ = make_client([FakeResponse(payload=PAGE_PAYLOAD), FakeResponse(payload=PAGE_PAYLOAD)], sleeps)
    client.get_page("A")
    client.get_page("B")
    assert sleeps == [1.1, 1.1]


def test_retries_after_server_error_and_network_error():
    sleeps = []
    responses = [FakeResponse(status_code=503), requests.ConnectionError("offline"), FakeResponse(payload=PAGE_PAYLOAD)]
    client, session = make_client(responses, sleeps)
    assert client.get_page("Rot Essence").title == "Rot Essence"
    assert len(session.calls) == 3
    assert sleeps == pytest.approx([1.1, 2.2, 3.3])


def test_gives_up_after_three_failed_attempts():
    client, session = make_client([FakeResponse(status_code=503)] * 3)
    with pytest.raises(WikiError, match="gave up after 3 attempts"):
        client.get_page("Owl")
    assert len(session.calls) == 3


def test_wiki_error_reply_fails_immediately_without_retry():
    reply = FakeResponse(payload={"error": {"code": "missingtitle", "info": "The page you specified doesn't exist."}})
    client, session = make_client([reply])
    with pytest.raises(WikiError, match="doesn't exist"):
        client.get_page("Not A Page")
    assert len(session.calls) == 1
