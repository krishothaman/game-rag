import time
from dataclasses import dataclass

import requests

from game_rag import config
from game_rag.titles import page_url


class WikiError(Exception):
    pass


@dataclass
class RawPage:
    requested_title: str
    title: str
    url: str
    html: str
    categories: list[str]


class WikiClient:
    def __init__(self, session=None, delay_seconds=config.REQUEST_DELAY_SECONDS, max_attempts=3, sleep=time.sleep):
        # session and sleep get swapped for fakes in the tests so we never hit the real wiki
        self.session = session if session is not None else requests.Session()
        self.session.headers["User-Agent"] = config.USER_AGENT
        self.delay_seconds = delay_seconds
        self.max_attempts = max_attempts
        self.sleep = sleep

    def get_category_members(self, category):
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmnamespace": "0",
            "cmlimit": "500",
        }
        titles = []
        while True:
            data = self._get(params)
            titles += [m["title"] for m in data["query"]["categorymembers"]]
            # wiki sends big lists in chunks, keep asking till theres no "continue"
            if "continue" not in data:
                return titles
            params = {**params, **data["continue"]}

    def get_page(self, title):
        # grabs the page html. redirects=1 bc stuff like Dragonrot is really Rot Essence
        data = self._get({
            "action": "parse",
            "page": title,
            "prop": "text|categories",
            "redirects": "1",
            "disableeditsection": "1",
            "disablelimitreport": "1",
        })
        parsed = data["parse"]
        return RawPage(
            requested_title=title,
            title=parsed["title"],
            url=page_url(parsed["title"]),
            html=parsed["text"],
            categories=[c["category"].replace("_", " ") for c in parsed.get("categories", [])],
        )

    def _get(self, params):
        params = {**params, "format": "json", "formatversion": "2"}
        problem = "no attempts made"
        for attempt in range(1, self.max_attempts + 1):
            # wait before every request, a bit longer on each retry
            self.sleep(self.delay_seconds * attempt)
            try:
                resp = self.session.get(config.API_URL, params=params, timeout=30)
            except requests.RequestException as e:
                problem = f"network error: {e}"
                continue
            # 429 = slow down, 5xx = wiki having a bad day. both worth another try
            if resp.status_code == 429 or resp.status_code >= 500:
                problem = f"HTTP {resp.status_code}"
                continue
            if resp.status_code >= 400:
                raise WikiError(f"HTTP {resp.status_code}")
            data = resp.json()
            if "error" in data:
                # eg page doesnt exist, retrying wont fix that
                raise WikiError(data["error"].get("info", "unknown wiki error"))
            return data
        raise WikiError(f"gave up after {self.max_attempts} attempts: {problem}")
