"""Offline, synthetic news fixtures and presentation-only aggregation for FinScope.

No live provider requests, scraping, model inference or external data dependencies.
The repository boundary allows a permitted data store to replace demo fixtures later.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, Protocol, Sequence

Sentiment = Literal["Positive", "Neutral", "Negative"]
TimeKind = Literal["published", "first_seen"]
SENTIMENTS = ("Positive", "Neutral", "Negative")
SECTORS = ("Technology", "Healthcare", "Materials", "Energy", "Financials")


@dataclass(frozen=True)
class ArticleRecord:
    article_id: str
    event_id: str
    title: str
    source: str
    sectors: tuple[str, ...]
    sentiment: Sentiment
    timestamp: datetime
    timestamp_kind: TimeKind
    summary: str = ""
    url: str | None = None
    synthetic: bool = True

    def __post_init__(self) -> None:
        if not self.article_id or not self.event_id or not self.title or not self.source:
            raise ValueError("Article, event, title and source identifiers are required")
        if not self.sectors or any(sector not in SECTORS for sector in self.sectors):
            raise ValueError("Article sectors must be selected from the supported taxonomy")
        if len(self.sectors) != len(set(self.sectors)):
            raise ValueError("Article sectors must be unique")
        if self.sentiment not in SENTIMENTS:
            raise ValueError("Unsupported sentiment")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone")
        if self.timestamp_kind not in ("published", "first_seen"):
            raise ValueError("Unsupported timestamp semantics")
        if self.synthetic and self.url:
            raise ValueError("Synthetic fixture must not imply a real source URL")


class NewsRepository(Protocol):
    def list_articles(self) -> list[ArticleRecord]: ...


@dataclass(frozen=True)
class SyntheticNewsRepository:
    anchor_day: date | None = None

    def list_articles(self) -> list[ArticleRecord]:
        day = self.anchor_day or datetime.now(timezone.utc).date()
        # All titles and sources are invented test fixtures, not actual reports.
        rows = [
            ("a01", "e01", "Demo: copper supply disruption raises metal prices", "Demo Wire A", ("Materials",), "Positive", 0),
            ("a02", "e01", "Demo: copper shortages lift benchmark commodity prices", "Demo Wire B", ("Materials",), "Positive", 0),
            ("a03", "e02", "Demo: semiconductor orders expand in fictional survey", "Demo Wire A", ("Technology",), "Positive", 0),
            ("a04", "e03", "Demo: software budgets contract in enterprise outlook", "Demo Wire C", ("Technology",), "Negative", 1),
            ("a05", "e04", "Demo: pharma research collaboration announced", "Demo Wire B", ("Healthcare",), "Neutral", 1),
            ("a06", "e05", "Demo: synthetic bank earnings match expectations", "Demo Wire C", ("Financials",), "Neutral", 1),
            ("a07", "e06", "Demo: lower oil demand weighs on energy outlook", "Demo Wire A", ("Energy",), "Negative", 2),
            ("a08", "e07", "Demo: health technology spending expands in pilot", "Demo Wire B", ("Healthcare", "Technology"), "Positive", 2),
            ("a09", "e07", "Demo: pilot study reports growth in health IT budgets", "Demo Wire C", ("Technology", "Healthcare"), "Positive", 2),
            ("a10", "e08", "Demo: synthetic chemicals report signals higher costs", "Demo Wire A", ("Materials",), "Negative", 3),
            ("a11", "e09", "Demo: insurance market outlook remains stable", "Demo Wire B", ("Financials",), "Neutral", 3),
            ("a12", "e10", "Demo: clean energy capital spending increases", "Demo Wire C", ("Energy",), "Positive", 4),
        ]
        return [
            ArticleRecord(
                article_id=article_id,
                event_id=event_id,
                title=title,
                source=source,
                sectors=sectors,
                sentiment=sentiment,
                timestamp=datetime.combine(day - timedelta(days=days_ago), time(12), tzinfo=timezone.utc),
                timestamp_kind="published",
                summary="Synthetic example for user-interface evaluation. Not a verified financial event.",
            )
            for article_id, event_id, title, source, sectors, sentiment, days_ago in rows
        ]


def filter_articles(
    articles: Sequence[ArticleRecord],
    *,
    start: date | None = None,
    end: date | None = None,
    sectors: Sequence[str] = (),
    sources: Sequence[str] = (),
    sentiments: Sequence[str] = (),
) -> list[ArticleRecord]:
    if start is not None and end is not None and start > end:
        raise ValueError("Start date cannot be after end date")
    selected_sectors, selected_sources, selected_sentiments = map(set, (sectors, sources, sentiments))
    return [
        a for a in articles
        if (start is None or a.timestamp.astimezone(timezone.utc).date() >= start)
        and (end is None or a.timestamp.astimezone(timezone.utc).date() <= end)
        and (not selected_sectors or bool(selected_sectors.intersection(a.sectors)))
        and (not selected_sources or a.source in selected_sources)
        and (not selected_sentiments or a.sentiment in selected_sentiments)
    ]


def unique_events(articles: Sequence[ArticleRecord]) -> list[ArticleRecord]:
    """One deterministic representative per event within the *filtered* result set.

    This is a UI display convention, NOT an event-level sentiment consensus model.
    """
    selected: dict[str, ArticleRecord] = {}
    for article in sorted(articles, key=lambda a: (a.timestamp, a.article_id)):
        selected.setdefault(article.event_id, article)
    return list(selected.values())


def sector_sentiment_counts(articles: Sequence[ArticleRecord]) -> list[dict[str, str | int]]:
    """An article/event contributes to each sector it is associated with."""
    counts: Counter[tuple[str, str]] = Counter(
        (sector, a.sentiment) for a in articles for sector in a.sectors
    )
    return [{"Sector": sector, **{s: counts[sector, s] for s in SENTIMENTS}} for sector in SECTORS]


def daily_sentiment_counts(
    articles: Sequence[ArticleRecord], *, start: date | None = None, end: date | None = None,
) -> list[dict[str, str | int]]:
    """UTC calendar counts, including zero days within the selected interval."""
    if start is not None and end is not None and start > end:
        raise ValueError("Start date cannot be after end date")
    filtered = filter_articles(articles, start=start, end=end)
    if not filtered:
        return []
    observed = [a.timestamp.astimezone(timezone.utc).date() for a in filtered]
    first, last = start or min(observed), end or max(observed)
    dates = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    counts = Counter((a.timestamp.astimezone(timezone.utc).date(), a.sentiment) for a in filtered)
    return [{"Date": day.isoformat(), **{s: counts[day, s] for s in SENTIMENTS}} for day in dates]


def headline_metrics(raw: Sequence[ArticleRecord], shown: Sequence[ArticleRecord]) -> dict[str, int | float]:
    counts = Counter(a.sentiment for a in shown)
    return {
        "raw_articles": len(raw),
        "unique_events": len({a.event_id for a in raw}),
        "sources": len({a.source for a in raw}),
        "positive_share": round(100 * counts["Positive"] / len(shown), 1) if shown else 0.0,
    }
