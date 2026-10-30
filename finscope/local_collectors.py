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
    "nist_rss": {"label":"NIST official news + permitted body text", "kind":"nist_rss", "publisher":"National Institute of Standards and Technology",
        "enabled":True,"access_status":"Official RSS and copyright policy reviewed 2026-10-31; runtime access checked per task",
        "bucket":"nist", "url":"https://www.nist.gov/news-events/news/rss.xml", "robots":"https://www.nist.gov/robots.txt",
        "scope":"Official news RSS and up to three linked staff-authored news text bodies; no media, attachments, pagination or copyrighted material",
        "terms_url":"https://www.nist.gov/copyrights-disclaimers", "attribution":"Source: NIST, U.S. Department of Commerce; original byline retained where supplied",
        "derivative_attribution":"Based on NIST information; FinScope analysis, no NIST endorsement",
        "exclusions":"Copyright-marked or special-rights text, third-party material, images, logos, software and research datasets excluded",
        "license":"NIST public-information reuse policy; unmarked official text", "license_url":"https://www.nist.gov/copyrights-disclaimers",
        "verified_on":"2026-10-31 Australia/Sydney", "body_limit":3,"http_budget":5,
        "minimum_interval_seconds":1,"timeout_seconds":15,"date_parser":"RSS RFC2822, preserve raw date", "content_level":"summary with optional body"},
    "rba_rss": {"label": "RBA RSS feed", "kind": "rss", "scope": "Official central-bank media releases", "url": rss_collector.FEED_URL},
    "rba_html": {"label": "RBA HTML media-release index", "kind": "html", "scope": "Official central-bank release index; dates only, no article body", "url": html_collector.INDEX_URL},
    "abs_html": {"label":"ABS media releases", "kind":"abs_html", "publisher":"Australian Bureau of Statistics",
        "enabled":True,"access_status":"HTTP 200 verified 2026-10-29T16:18:13Z",
        "bucket":"abs", "url":"https://www.abs.gov.au/media-centre/media-releases", "robots":"https://www.abs.gov.au/robots.txt",
        "scope":"Official release-index headlines and publication dates; one page, no article bodies",
        "terms_url":"https://www.abs.gov.au/website-privacy-copyright-and-disclaimer",
        "attribution":"Source: Australian Bureau of Statistics, © Commonwealth of Australia",
        "derivative_attribution":"Based on Australian Bureau of Statistics material; FinScope analysis, no ABS endorsement",
        "exclusions":"Third-party content, logos, trademarks, microdata and separately restricted material excluded",
        "license":"CC BY 4.0", "license_url":"https://creativecommons.org/licenses/by/4.0/", "verified_on":"2026-10-30 Australia/Sydney"},
    "accc_rss": {"label":"ACCC media releases RSS", "kind":"accc_rss", "publisher":"Australian Competition and Consumer Commission",
        "enabled":False,"access_status":"HTTP 403 observed 2026-10-29T16:19:05Z; no retry or alternative endpoint attempted",
        "bucket":"accc", "url":"https://www.accc.gov.au/rss/media_releases.xml", "robots":"https://www.accc.gov.au/robots.txt",
        "scope":"Official RSS headlines and supplied descriptions; no linked pages, media or attachments",
        "terms_url":"https://www.accc.gov.au/about-us/using-our-website/disclaimer-and-copyright",
        "attribution":"Source: ACCC © Commonwealth of Australia",
        "derivative_attribution":"Source: Based on ACCC data or other content; FinScope analysis, no ACCC endorsement",
        "exclusions":"Third-party content, logos, Coat of Arms and separately restricted material excluded",
        "license":"CC BY 4.0", "license_url":"https://creativecommons.org/licenses/by/4.0/", "verified_on":"2026-10-30 Australia/Sydney"},
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
