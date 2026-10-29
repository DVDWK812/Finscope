"""Fixed RBA collector integration and strict import of existing local outputs."""
from dataclasses import asdict
from datetime import date
import json

from .api_sources import Article, QueryResult
from .local_news import FetchBlocked, NewsItem, utcnow
from . import rss_collector, html_collector

# Fixed, reviewed collector registry. Adding a source requires its own validation
# and permission review; no user URL or generic crawling adapter is accepted.
SOURCES = {
    "rba_rss": {"label": "RBA RSS feed", "kind": "rss", "scope": "Official central-bank media releases", "url": rss_collector.FEED_URL},
    "rba_html": {"label": "RBA HTML media-release index", "kind": "html", "scope": "Official central-bank release index; dates only, no article body", "url": html_collector.INDEX_URL},
}


def collector_items(articles, provenance, rights):
    rights.require("preview")
    if len(articles)!=len(provenance) or len(articles)>100:
        raise ValueError("Invalid collector output")
    result=[]
    for article, evidence in zip(articles,provenance):
        if (not isinstance(evidence,dict) or not all(isinstance(value,str) for value in asdict(article).values())
                or len(article.title)>300 or len(article.description)>10000 or not article.title.strip()
                or article.timestamp_kind!="published"):
            raise ValueError("Invalid collector record")
        if article.provider=="rba_rss":
            if (article.source!=rss_collector.SOURCE or not rss_collector._official_link(article.url)
                    or article.timestamp and rss_collector._publication(article.timestamp)!=article.timestamp):
                raise ValueError("RSS import must preserve official RBA metadata")
        elif article.provider=="rba_html":
            if (article.source!=html_collector.SOURCE or not article.url
                    or html_collector._release_url(article.url)!=article.url or article.timestamp or article.description):
                raise ValueError("HTML import must preserve official index-only metadata")
        else:
            raise ValueError("Only existing RBA RSS/HTML output is supported")
        day=evidence.get("publication_date","")
        if day:
            date.fromisoformat(day)
        safe={key:value for key,value in evidence.items() if key in {"attribution","publication_time_original",
              "publication_date_original","publication_date","timestamp_precision","feed_source_element","url"}
              and isinstance(value,str) and len(value)<=1000}
        item=NewsItem.from_article(article,rights,publication_date=day)
        from dataclasses import replace
        result.append(replace(item,provenance=json.dumps(safe,ensure_ascii=False)))
    return result


def import_output(payload,rights):
    if not isinstance(payload,bytes) or len(payload)>1024*1024:
        raise ValueError("Import a collector JSON file no larger than 1 MiB")
    try:
        rows=json.loads(payload.decode("utf-8-sig"))
        if not isinstance(rows,list) or not 1<=len(rows)<=100:
            raise ValueError
        articles=[Article(**row["article"]) for row in rows]
        provenance=[row["provenance"] for row in rows]
        return collector_items(articles,provenance,rights)
    except (ValueError,TypeError,KeyError,AttributeError):
        raise ValueError("Invalid RBA collector JSON; no records were imported") from None


def collect_rba(service,kind,rights,*,explicit=False,collect=None):
    rights.require("preview")
    if explicit is not True or kind not in {"rss","html"}:
        raise FetchBlocked("An explicit fixed-source collection action is required")
    request_id,now=service._reserve("rba",1)
    try:
        operation=collect or (rss_collector.collect_once if kind=="rss" else html_collector.collect_once)
        output=operation(limit=3)
        items=collector_items(output["articles"],output["provenance"],rights)
        status="ok"
    except Exception:
        items=[];status="failed"
    from contextlib import closing
    with closing(service.store.connect()) as db:
        db.execute("UPDATE local_requests SET completed_at=?,status=?,outcome=? WHERE id=?",
                   (utcnow().isoformat(),status,"records" if items else "empty" if status=="ok" else "collector_error",request_id))
        db.commit()
    if status!="ok":
        raise FetchBlocked("RBA collection failed; no retry was made. Review the local ledger before another attempt")
    return items
