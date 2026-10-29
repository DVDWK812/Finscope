"""Local product ingestion, persistent originals and durable request reservations.

No network operation happens on construction or reads. Keys are call arguments,
never fields, SQL values, diagnostics or cache keys. The study sampler is retained
unchanged; this separately authorized local workflow respects its existing holds.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from .api_sources import Article, QueryResult, fetch_provider, _http_get_json
from .demo_pipeline import ApprovedSubmission, DemoRecord, classify_sectors
from .rate_limits import COOLDOWN_PATH, load_cooldowns, retry_deadline
from .sampling import LEDGER_PATH
from .ui_data import ArticleRecord


SOURCE_OPTIONS = {"Marketaux": "marketaux", "NewsData.io": "newsdata", "Finnhub": "finnhub",
                  "Local Collector": "local"}
SOURCE_NOTES = {
    "marketaux": "Financial keyword feed · at most 3 records/request on the free plan. Date filters do not guarantee free historical access.",
    "newsdata": "Latest feed only, approximately 48 hours; free access may be delayed. No archive request is made. Existing manual pause remains active.",
    "finnhub": "Ticker-specific company news, not sector-wide coverage. Date-range access depends on your plan; no complete-history claim.",
    "local": "Fixed RBA RSS or media-release index only. No arbitrary websites or full-article crawling.",
}


def utcnow():
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ContentRights:
    preview: bool = False
    retain: bool = False
    analyze: bool = False
    external: bool = False
    reference: str = ""

    def require(self, action):
        if (action not in {"preview", "retain", "analyze", "external"}
                or getattr(self, action) is not True or not self.reference.strip()):
            raise ValueError(f"Permission to {action} this text has not been supplied")


@dataclass(frozen=True)
class NewsItem:
    article_id: str
    provider: str
    title: str
    source: str
    url: str
    summary: str = field(repr=False)
    timestamp: str
    timestamp_kind: str
    fetched_at: str
    sectors: tuple[str, ...]
    rights: ContentRights
    publication_date: str = ""  # Date-only collector evidence, never midnight UTC.
    company: str = ""  # Evidence: returned by a ticker-specific company feed.
    provenance: str = "provider headline and available summary"

    @property
    def record_date(self):
        return self.timestamp[:10] or self.publication_date

    @property
    def analysis_text(self):
        return self.title + ("\n" + self.summary if self.summary else "")

    @classmethod
    def from_article(cls, article, rights, *, now=None, company="", publication_date=""):
        return cls(uuid4().hex, article.provider, article.title, article.source, article.url,
                   article.description, article.timestamp, article.timestamp_kind,
                   (now or utcnow()).isoformat(), tuple(classify_sectors(article.title+" "+article.description)),
                   rights, publication_date, company)


@dataclass(frozen=True)
class Analysis:
    analysis_id: str
    article_id: str
    label: str
    family: str
    model_id: str
    revision: str
    analyzed_at: str
    probabilities: dict | None = None
    rationale: str = ""
    candidate_id: str = ""
    embedding_revision: str = ""
    similarity: float | None = None
    elapsed_ms: float = 0
    demo_record: dict | None = field(default=None, repr=False)


class LocalNewsStore:
    """Single-user local SQLite. Records survive browser and app restarts."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS local_news (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS local_analyses (id TEXT PRIMARY KEY, article_id TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS local_settings (name TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS local_requests (id TEXT PRIMARY KEY, provider TEXT NOT NULL,
                    reserved_at TEXT NOT NULL, completed_at TEXT, status TEXT NOT NULL,
                    http_status INTEGER, hold_until TEXT, outcome TEXT);
            """)
            db.commit()

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def setting(self, name, default=None):
        with closing(self.connect()) as db:
            row = db.execute("SELECT value FROM local_settings WHERE name=?", (name,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, name, value):
        # Only product preferences. Credentials can never enter this table.
        if name not in {"guide_completed"} or type(value) is not bool:
            raise ValueError("Unsupported local preference")
        with closing(self.connect()) as db:
            db.execute("INSERT OR REPLACE INTO local_settings VALUES (?,?)", (name, json.dumps(value)))
            db.commit()

    def save_news(self, item):
        item.rights.require("retain")
        item.rights.require("preview")
        with closing(self.connect()) as db:
            db.execute("INSERT OR IGNORE INTO local_news VALUES (?,?)", (item.article_id, json.dumps(asdict(item))))
            db.commit()

    def list_news(self):
        with closing(self.connect()) as db:
            rows = db.execute("SELECT payload FROM local_news ORDER BY rowid").fetchall()
        result = []
        for (payload,) in rows:
            data = json.loads(payload)
            data["rights"] = ContentRights(**data["rights"])
            data["sectors"] = tuple(data["sectors"])
            result.append(NewsItem(**data))
        return result

    def save_analysis(self, analysis):
        with closing(self.connect()) as db:
            if not db.execute("SELECT 1 FROM local_news WHERE id=?", (analysis.article_id,)).fetchone():
                raise ValueError("Save the permitted original before analysis")
            db.execute("INSERT INTO local_analyses VALUES (?,?,?,?)", (analysis.analysis_id,
                       analysis.article_id, analysis.analyzed_at, json.dumps(asdict(analysis))))
            db.commit()

    def list_analyses(self):
        with closing(self.connect()) as db:
            rows = db.execute("SELECT payload FROM local_analyses ORDER BY analyzed_at,rowid").fetchall()
        return [Analysis(**json.loads(row[0])) for row in rows]

    def latest_analyses(self):
        return {a.article_id: a for a in self.list_analyses()}

    def export(self):
        return {"news": [asdict(n) for n in self.list_news()],
                "analyses": [asdict(a) for a in self.list_analyses()]}


class FetchBlocked(ValueError):
    """Fixed local reason, never an exception or remote response body."""


class LocalIngestionService:
    def __init__(self, store, *, cooldown_path=COOLDOWN_PATH, study_path=LEDGER_PATH,
                 transport=_http_get_json, clock=utcnow):
        self.store, self.cooldown_path, self.study_path = store, Path(cooldown_path), Path(study_path)
        self.transport, self.clock = transport, clock

    def _reserve(self, provider, remaining):
        now = self.clock()
        if type(remaining) is not int or not 1 <= remaining <= 10000:
            raise FetchBlocked("Confirm a positive remaining account quota before Fetch")
        try:
            holds = load_cooldowns(self.cooldown_path)
        except (OSError, ValueError):
            raise FetchBlocked("Existing provider cooldown state needs review") from None
        if holds.get(provider, now) > now:
            raise FetchBlocked("Existing provider cooldown is still active")
        # Never bypass an unresolved reservation or hold in the preserved study.
        if provider == "marketaux" and self.study_path.exists():
            try:
                with closing(sqlite3.connect(self.study_path.resolve().as_uri()+"?mode=ro", uri=True)) as study:
                    rows = study.execute("SELECT reserved_at,completed_at,status,cooldown_until FROM attempts").fetchall()
                for reserved, completed, status, hold in rows:
                    if status == "attempted_outcome_unknown":
                        raise FetchBlocked("Existing study has an unresolved request; review before fetching")
                    end = datetime.fromisoformat(completed or reserved)
                    if (now-end < timedelta(seconds=60)
                            or hold and datetime.fromisoformat(hold) > now):
                        raise FetchBlocked("Existing study spacing or cooldown is active")
                    if status in {"failed", "review_failed"} and end.date() == now.date():
                        raise FetchBlocked("Existing study stopped today's provider requests")
            except (sqlite3.Error, ValueError) as error:
                if isinstance(error, FetchBlocked):
                    raise
                raise FetchBlocked("Existing study ledger needs review") from None
        request_id = uuid4().hex
        with closing(self.store.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT reserved_at,completed_at,status,hold_until FROM local_requests WHERE provider=?", (provider,)).fetchall()
            today = 0
            for reserved, completed, status, hold in rows:
                start, end = datetime.fromisoformat(reserved), datetime.fromisoformat(completed or reserved)
                if status == "pending":
                    raise FetchBlocked("A previous request has an unknown outcome; inspect the local ledger")
                if hold and datetime.fromisoformat(hold) > now:
                    raise FetchBlocked("Provider Retry-After hold is active")
                if now-end < timedelta(seconds=60):
                    raise FetchBlocked("Wait at least 60 seconds between provider requests")
                if start.date() == now.date():
                    today += 1
                    if status == "failed":
                        raise FetchBlocked("A provider failure stopped further requests for this UTC day")
            if today >= 3:
                raise FetchBlocked("Local safety cap reached: 3 requests/provider/UTC day")
            db.execute("INSERT INTO local_requests(id,provider,reserved_at,status) VALUES (?,?,?,?)",
                       (request_id, provider, now.isoformat(), "pending"))
            db.commit()  # Durable intent before dispatch, including transport failures.
        return request_id, now

    def fetch(self, provider, topic, *, api_key, rights, remaining, days=2, symbol=None, explicit=False):
        if explicit is not True:
            raise FetchBlocked("An explicit Fetch action is required")
        if provider not in {"marketaux", "newsdata", "finnhub"}:
            raise FetchBlocked("Choose a supported API source")
        if provider == "newsdata":
            raise FetchBlocked("NewsData.io remains manually paused; no request was made")
        rights.require("preview")
        if not isinstance(api_key, str) or not api_key.strip() or len(api_key) > 500:
            raise FetchBlocked("Enter an API key or configure the project's local .env")
        if type(days) is not int or not 1 <= days <= 30:
            raise FetchBlocked("Choose a lookback between 1 and 30 days; account history is not guaranteed")
        # Validate inputs before consuming a reservation.
        from .api_sources import build_request
        build_request(provider, topic, self.clock(), days, 3, api_key, symbol=symbol)
        request_id, now = self._reserve(provider, remaining)
        result = fetch_provider(provider, topic, now=now, days=days, limit=3, timeout=15,
                                api_key=api_key, symbol=symbol, transport=self.transport)
        # A malicious/upstream echo must never become a preview, SQL row or log.
        if any(api_key in value for a in result.articles for value in asdict(a).values()):
            result = QueryResult(provider, topic, result.query_mode, "failed", [],
                                 http_status=result.http_status, outcome="unsafe_response", note="Response withheld")
        finished = self.clock()
        retry = result.rate_limit_headers.get("Retry-After")
        hold = retry_deadline(retry, finished) if retry or result.http_status == 429 else None
        if result.rate_limit_headers.get("X-RateLimit-Remaining") == "0":
            hold = max(hold or finished, finished+timedelta(hours=24))
        with closing(self.store.connect()) as db:
            db.execute("UPDATE local_requests SET completed_at=?,status=?,http_status=?,hold_until=?,outcome=? WHERE id=?",
                       (finished.isoformat(), result.status, result.http_status, hold.isoformat() if hold else None,
                        result.outcome, request_id))
            db.commit()
        items = [NewsItem.from_article(a, rights, now=now, company=symbol or "" if provider == "finnhub" else "")
                 for a in result.articles]
        return result, items


def _demo_payload(record):
    data = asdict(record)
    data["article"]["timestamp"] = record.article.timestamp.isoformat()
    return json.loads(json.dumps(data))


def _demo_record(data):
    data = dict(data)
    article = dict(data.pop("article"))
    article["timestamp"] = datetime.fromisoformat(article["timestamp"])
    article["sectors"] = tuple(article["sectors"])
    return DemoRecord(article=ArticleRecord(**article), **data)


def analyze_finbert(item, store, pipeline):
    """Reuse the unchanged approved-input pipeline and frozen grouping rules."""
    item.rights.require("analyze")
    item.rights.require("retain")
    # Unknown exact publication time is not replaced by collection/submission time.
    if not item.timestamp:
        raise ValueError("Exact publication time is unavailable; use an approved text submission with its actual timestamp meaning")
    submission = ApprovedSubmission(item.analysis_text, item.title, item.source,
                    datetime.fromisoformat(item.timestamp), item.timestamp_kind,
                    "synthetic" if item.provider == "authored_synthetic" else "licensed",
                    item.rights.reference, True, item.url or None)
    submission.validate()
    previous = [a for a in store.latest_analyses().values() if a.demo_record and a.article_id != item.article_id]

    class PipelineRepository:
        def check_session(self, _session):
            pass
        def list_records(self, _session):
            return [_demo_record(a.demo_record) for a in previous]
        def save(self, _session, _record):
            pass  # The final record is stored atomically with its stable original ID below.

    record = pipeline.submit(submission, PipelineRepository(), "0"*32)
    record = replace(record, article=replace(record.article, article_id=item.article_id))
    analysis = Analysis(uuid4().hex, item.article_id, record.article.sentiment, "FinBERT", "ProsusAI/finbert",
                        record.model_revision, utcnow().isoformat(), record.scores,
                        candidate_id=record.article.event_id, embedding_revision=record.embedding_revision,
                        similarity=record.similarity, elapsed_ms=record.inference_ms, demo_record=_demo_payload(record))
    store.save_analysis(analysis)
    return analysis
