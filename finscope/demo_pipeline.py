"""Approved-text MVP pipeline. No news API imports or network ingestion."""

from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re
import sqlite3
from threading import RLock
from urllib.parse import urlsplit
from uuid import uuid4

from .ai_prototype import EvaluationText
from .ui_data import ArticleRecord


RULES = {
    "Technology": ("software", "semiconductor", "chip", "chipmaker", "cloud", "artificial intelligence", "technology"),
    "Healthcare": ("healthcare", "hospital", "pharma", "pharmaceutical", "biotech", "drug", "medical"),
    "Materials": ("copper", "metal", "mining", "mine", "steel", "chemical", "materials"),
    "Energy": ("oil", "gas", "energy", "solar", "wind", "renewable"),
    "Financials": ("bank", "banking", "insurance", "insurer", "financial", "lending", "loan"),
}
SIMILARITY_THRESHOLD = 0.80  # Declared before evaluation; not learned/calibrated.
MAX_SESSION_RECORDS = 100


def classify_sectors(text: str) -> dict[str, list[str]]:
    evidence = {sector: [word for word in words if re.search(r"\b"+re.escape(word)+r"s?\b", text.casefold())]
                for sector, words in RULES.items()}
    return {sector: matches for sector, matches in evidence.items() if matches} or {"Unclassified": []}


def cosine(left, right) -> float:
    if len(left) != len(right) or not left or not all(math.isfinite(x) for x in [*left, *right]):
        raise ValueError("Invalid embedding dimensions or values")
    a, b = math.hypot(*left), math.hypot(*right)
    if not a or not b:
        raise ValueError("Zero embedding vector")
    return max(-1., min(1., math.fsum((x/a)*(y/b) for x, y in zip(left, right))))


@dataclass(frozen=True)
class ApprovedSubmission:
    text: str = field(repr=False)
    title: str
    source: str
    timestamp: datetime
    timestamp_kind: str
    origin: str
    permission_reference: str = field(repr=False)
    rights_confirmed: bool = False
    url: str | None = None

    def validate(self) -> EvaluationText:
        if self.rights_confirmed is not True:
            raise ValueError("Confirm your right to process and store this demo text")
        record = EvaluationText(self.text, self.origin, self.permission_reference)
        if (not isinstance(self.title, str) or not self.title.strip() or len(self.title) > 160
                or not isinstance(self.source, str) or not self.source.strip() or len(self.source) > 100
                or not self.permission_reference.strip() or len(self.permission_reference) > 300):
            raise ValueError("Provide a short title, source and permission reference")
        if (not isinstance(self.timestamp,datetime) or self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None
                or self.timestamp > datetime.now(timezone.utc)+timedelta(minutes=5)
                or self.timestamp_kind not in {"published", "first_seen", "submitted"}):
            raise ValueError("Use a valid timezone-aware time and its actual meaning")
        if self.url:
            parsed = urlsplit(self.url)
            if (self.origin == "synthetic" or len(self.url) > 1000 or parsed.scheme not in {"https", "http"}
                    or not parsed.hostname or parsed.username or parsed.password):
                raise ValueError("Use a plain public source URL only for licensed text")
        return record


@dataclass(frozen=True)
class DemoRecord:
    article: ArticleRecord
    text: str = field(repr=False)
    origin: str
    scores: dict
    sector_evidence: dict
    vector: list = field(repr=False)
    model_revision: str
    embedding_revision: str
    similarity: float | None
    inference_ms: float
    permission_reference: str = ""
    sector_rule_version: str = "legacy-unversioned"


class ApprovedDemoRepository:
    """Session-scoped SQLite; never reads pilot reports or API state.

    No shared user-text gallery. Server storage is disposable on free hosts;
    export is provided by the UI. Expired records are purged on app access,
    not by a background deletion service.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS demo_records (
                id TEXT PRIMARY KEY, session_id TEXT NOT NULL, created_at TEXT NOT NULL,
                payload TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS demo_session ON demo_records(session_id)")
            db.execute("DELETE FROM demo_records WHERE created_at < ?",
                       ((datetime.now(timezone.utc)-timedelta(hours=24)).isoformat(),))
            db.commit()

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    @staticmethod
    def check_session(session_id):
        if not isinstance(session_id, str) or not re.fullmatch(r"[a-f0-9]{32}", session_id):
            raise ValueError("Invalid demo workspace")

    def list_records(self, session_id: str) -> list[DemoRecord]:
        self.check_session(session_id)
        with closing(self.connect()) as db:
            rows = db.execute("SELECT payload FROM demo_records WHERE session_id=? ORDER BY created_at,id LIMIT 100",
                              (session_id,)).fetchall()
        records = []
        for (payload,) in rows:
            data = json.loads(payload)
            article = data.pop("article")
            article["timestamp"] = datetime.fromisoformat(article["timestamp"])
            article["sectors"] = tuple(article["sectors"])
            records.append(DemoRecord(article=ArticleRecord(**article), **data))
        return records

    def save(self, session_id: str, record: DemoRecord) -> None:
        self.check_session(session_id)
        data = asdict(record)
        data["article"]["timestamp"] = record.article.timestamp.isoformat()
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT count(*) FROM demo_records WHERE session_id=?", (session_id,)).fetchone()[0]
            total = db.execute("SELECT count(*) FROM demo_records").fetchone()[0]
            if count >= MAX_SESSION_RECORDS or total >= 1000:
                raise ValueError("Demo capacity reached; export your current results")
            db.execute("INSERT INTO demo_records VALUES (?,?,?,?)", (record.article.article_id, session_id,
                       datetime.now(timezone.utc).isoformat(), json.dumps(data)))
            db.commit()


class DemoPipeline:
    def __init__(self, sentiment, embedder, *, sentiment_backend=None):
        self.sentiment = sentiment
        self.embedder = embedder
        self.sentiment_backend = sentiment_backend
        self.lock = RLock()

    def submit(self, submission: ApprovedSubmission, repository: ApprovedDemoRepository,
               session_id: str) -> DemoRecord:
        import time
        text = submission.validate()
        repository.check_session(session_id)
        with self.lock:
            previous = repository.list_records(session_id)
            if len(previous) >= MAX_SESSION_RECORDS:
                raise ValueError("Demo record limit reached")
            # Check both token budgets before either model executes.
            if self.sentiment_backend is not None:
                self.sentiment_backend.tokenize([text.text])
            self.embedder.tokenize([text.text])
            started = time.perf_counter()
            prediction = self.sentiment.predict([text])[0]
            vector = self.embedder.encode([text.text])[0]
            elapsed = (time.perf_counter()-started)*1000
            evidence = classify_sectors(submission.title+" "+text.text)
            # Representative-only matching avoids unrestricted transitive chains.
            representatives = {}
            for old in sorted(previous, key=lambda r:(r.article.timestamp,r.article.article_id)):
                representatives.setdefault(old.article.event_id, old)
            best, similarity = None, -1.0
            for old in representatives.values():
                if old.embedding_revision != self.embedder.revision:
                    continue
                if abs((old.article.timestamp-submission.timestamp).total_seconds()) > 72*3600:
                    continue
                score = cosine(vector, old.vector)
                if score > similarity:
                    best, similarity = old, score
            event_id = best.article.event_id if best and similarity >= SIMILARITY_THRESHOLD else uuid4().hex
            article = ArticleRecord(uuid4().hex, event_id, submission.title.strip(), submission.source.strip(),
                                    tuple(evidence), prediction.label.capitalize(), submission.timestamp,
                                    submission.timestamp_kind, summary=text.text, url=submission.url,
                                    synthetic=submission.origin == "synthetic")
            record = DemoRecord(article, text.text, submission.origin,
                                {key:getattr(prediction,key) for key in ("positive","negative","neutral")},
                                evidence, vector, prediction.revision, self.embedder.revision,
                                similarity if best else None, round(elapsed,2),
                                submission.permission_reference,"keyword-v1")
            repository.save(session_id, record)
            return record
