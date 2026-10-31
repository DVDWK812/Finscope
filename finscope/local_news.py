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
import hashlib
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
    "local": "Fixed RBA and ABS sources; ACCC access is currently unavailable. No arbitrary websites, pagination or article-body crawling.",
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
    body: str = field(default="", repr=False)
    processed_text: str = field(default="", repr=False)
    content_version: str = ""
    language: str = "unknown"
    text_basis: str = ""

    @property
    def record_date(self):
        return (datetime.fromisoformat(self.timestamp).astimezone(timezone.utc).date().isoformat()
                if self.timestamp else self.publication_date)

    @property
    def published_day(self):
        """Never substitute first-seen, submitted, ingestion or inference time."""
        return self.record_date if self.timestamp_kind == "published" else ""

    @property
    def analysis_text(self):
        return self.processed_text or self.title + ("\n" + self.summary if self.summary else "")

    @classmethod
    def from_article(cls, article, rights, *, now=None, company="", publication_date=""):
        identity = (hashlib.sha256(json.dumps(asdict(article),sort_keys=True).encode()).hexdigest()[:32]
                    if article.url else uuid4().hex)
        return cls(identity, article.provider, article.title, article.source, article.url,
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
    provenance: dict = field(default_factory=dict)


class LocalNewsStore:
    """Single-user local SQLite. Records survive browser and app restarts."""
    def __init__(self, path):
        from .test_safety import require_test_path
        require_test_path(path)
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
                CREATE TABLE IF NOT EXISTS local_model_requests (id TEXT PRIMARY KEY, backend TEXT NOT NULL,
                    reserved_at TEXT NOT NULL, completed_at TEXT, status TEXT NOT NULL, hold_until TEXT);
                CREATE TABLE IF NOT EXISTS local_permission_history (article_id TEXT NOT NULL,
                    changed_at TEXT NOT NULL, previous_rights TEXT NOT NULL, new_rights TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS local_collector_http (id TEXT PRIMARY KEY, action_id TEXT NOT NULL,
                    source_id TEXT NOT NULL, url TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT,
                    status TEXT NOT NULL, http_status INTEGER, response_bytes INTEGER);
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

    def update_rights(self, article_id, rights):
        rights.require("preview")
        rights.require("retain")
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM local_news WHERE id=?",(article_id,)).fetchone()
            if row is None:
                raise ValueError("Original article not found")
            data = json.loads(row[0])
            db.execute("INSERT INTO local_permission_history VALUES (?,?,?,?)",(article_id,utcnow().isoformat(),
                       json.dumps(data["rights"]),json.dumps(asdict(rights))))
            data["rights"] = asdict(rights)
            db.execute("UPDATE local_news SET payload=? WHERE id=?",(json.dumps(data),article_id))
            db.commit()

    def save_analysis(self, analysis, *, transaction=None):
        if transaction is not None:
            if not transaction.execute('SELECT 1 FROM local_news WHERE id=?',(analysis.article_id,)).fetchone():
                raise ValueError('Save the permitted original before analysis')
            transaction.execute('INSERT INTO local_analyses VALUES (?,?,?,?)',(analysis.analysis_id,
                analysis.article_id,analysis.analyzed_at,json.dumps(asdict(analysis))))
            return
        with closing(self.connect()) as db:
            self.save_analysis(analysis,transaction=db)
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


@dataclass(frozen=True)
class SourceStatus:
    state: str
    reason: str
    blocked: bool = False
    last_attempt: str = ""
    last_outcome: str = ""


class LocalIngestionService:
    def __init__(self, store, *, cooldown_path=COOLDOWN_PATH, study_path=LEDGER_PATH,
                 transport=_http_get_json, clock=utcnow):
        self.store, self.cooldown_path, self.study_path = store, Path(cooldown_path), Path(study_path)
        self.transport, self.clock = transport, clock

    def _check_holds(self, provider, now, local_rows):
        """Shared read-only guard for status and transactional reservation."""
        now = now.astimezone(timezone.utc)
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
                    study_rows = study.execute("SELECT reserved_at,completed_at,status,cooldown_until FROM attempts").fetchall()
                for reserved, completed, status, hold in study_rows:
                    if status == "attempted_outcome_unknown":
                        raise FetchBlocked("Existing study has an unresolved request; review before fetching")
                    end = datetime.fromisoformat(completed or reserved).astimezone(timezone.utc)
                    if (now-end < timedelta(seconds=60)
                            or hold and datetime.fromisoformat(hold) > now):
                        raise FetchBlocked("Existing study spacing or cooldown is active")
                    if status in {"failed", "review_failed"} and end.date() == now.date():
                        raise FetchBlocked("Existing study stopped today's provider requests")
            except (sqlite3.Error, ValueError) as error:
                if isinstance(error, FetchBlocked):
                    raise
                raise FetchBlocked("Existing study ledger needs review") from None
        today = 0
        for reserved, completed, status, hold in local_rows:
            start = datetime.fromisoformat(reserved).astimezone(timezone.utc)
            end = datetime.fromisoformat(completed or reserved).astimezone(timezone.utc)
            if status == "pending":
                raise FetchBlocked("A previous request has an unknown outcome; inspect the local ledger")
            if hold and datetime.fromisoformat(hold) > now:
                raise FetchBlocked("Provider Retry-After hold is active")
            if now-end < timedelta(seconds=60):
                raise FetchBlocked("Wait at least 60 seconds between provider requests")
            if status == "failed" and end.date() == now.date():
                raise FetchBlocked("A provider failure stopped further requests for this UTC day")
            if start.date() == now.astimezone(timezone.utc).date():
                today += 1
        if today >= 3:
            raise FetchBlocked("Local safety cap reached: 3 requests/provider/UTC day")

    def source_status(self, provider, *, configured):
        """No probe or reservation. Historical failures are not permanent outages."""
        if provider == "newsdata":
            return SourceStatus("Paused", "Existing manual pause; no requests allowed", True)
        with closing(self.store.connect()) as db:
            local_rows = db.execute("SELECT reserved_at,completed_at,status,hold_until FROM local_requests WHERE provider=? ORDER BY reserved_at", (provider,)).fetchall()
        last = local_rows[-1] if local_rows else None
        stamp, outcome = (last[1] or last[0], last[2]) if last else ("", "")
        try:
            self._check_holds(provider, self.clock(), local_rows)
        except (FetchBlocked, ValueError, OSError):
            import sys
            error = sys.exception()
            reason = str(error) if isinstance(error, FetchBlocked) else "Local request state needs review"
            return SourceStatus("Failed" if outcome == "failed" else "Paused", reason, True, stamp, outcome)
        if not configured:
            return SourceStatus("Not configured", "Enter this source's key or configure its local .env variable", False, stamp, outcome)
        if outcome == "ok":
            return SourceStatus("Available", "Last request succeeded; this is not a live connection probe", False, stamp, outcome)
        return SourceStatus("Untested", "Configured; no current successful connection check", False, stamp, outcome)

    def _reserve(self, provider, remaining):
        now = self.clock()
        if type(remaining) is not int or not 1 <= remaining <= 10000:
            raise FetchBlocked("Confirm a positive remaining account quota before Fetch")
        request_id = uuid4().hex
        with closing(self.store.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            local_rows = db.execute("SELECT reserved_at,completed_at,status,hold_until FROM local_requests WHERE provider=?", (provider,)).fetchall()
            self._check_holds(provider, now, local_rows)
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
    # The model can analyze a permitted headline with unknown publication time.
    # For pipeline validation only, use the actual ingestion time as submitted;
    # disable temporal grouping and never write that time back to the original.
    has_exact_time = bool(item.timestamp)
    submission = ApprovedSubmission(item.analysis_text, item.title if len(item.title)<=160 else "Financial news headline",
                    item.source if len(item.source)<=100 else "Provider source; see original metadata",
                    datetime.fromisoformat(item.timestamp or item.fetched_at), item.timestamp_kind if has_exact_time else "submitted",
                    "synthetic" if item.provider == "authored_synthetic" else "licensed",
                    item.rights.reference, True, item.url or None)
    submission.validate()
    previous = [a for a in store.latest_analyses().values() if a.demo_record and a.article_id != item.article_id] if has_exact_time else []

    class PipelineRepository:
        def check_session(self, _session):
            pass
        def list_records(self, _session):
            return [_demo_record(a.demo_record) for a in previous]
        def save(self, _session, _record):
            pass  # The final record is stored atomically with its stable original ID below.

    record = pipeline.submit(submission, PipelineRepository(), "0"*32)
    record = replace(record, article=replace(record.article, article_id=item.article_id,title=item.title,source=item.source))
    analysis = Analysis(uuid4().hex, item.article_id, record.article.sentiment, "FinBERT", "ProsusAI/finbert",
                        record.model_revision, utcnow().isoformat(), record.scores,
                        candidate_id=record.article.event_id if has_exact_time else "", embedding_revision=record.embedding_revision,
                        similarity=record.similarity, elapsed_ms=record.inference_ms,
                        demo_record=_demo_payload(record) if has_exact_time else None,
                        provenance={"output_kind":"actual_model_inference","text_basis":"headline_and_supplied_summary" if item.summary else "headline_only",
                                    "temporal_grouping":"unverified_candidate" if has_exact_time else "disabled_unknown_publication_time"})
    store.save_analysis(analysis)
    return analysis
