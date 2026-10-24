"""Bounded, transient description review; returns categories/counts, never text.

Rules detect missing/exact repetition only. Added facts and boilerplate require
an explicit annotator; an unreviewed description is uncertain, not informative.
This module makes no sentiment, independent-review or accuracy claim.
"""

from dataclasses import asdict, dataclass
from enum import Enum
import re
from typing import Callable, Sequence

from .api_sources import Article


class Quality(str, Enum):
    MISSING = "missing"
    REPETITION = "title_repetition"
    BOILERPLATE = "boilerplate"
    ADDS_FACT = "adds_concrete_fact"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class DescriptionReview:
    sample_index: int
    category: Quality
    basis: str
    title_chars: int
    description_chars: int
    description_words: int
    over_limit: bool = False

    def safe_dict(self) -> dict:
        return {**asdict(self), "category": self.category.value}


Annotator = Callable[[str, str], Quality]
MAX_SAMPLES = 3
MAX_TITLE_CHARS = 500
MAX_DESCRIPTION_CHARS = 2000


def review_descriptions(articles: Sequence[Article], annotator: Annotator | None = None
                        ) -> tuple[DescriptionReview, ...]:
    """Inspect at most three short fields in memory; never save/echo callbacks.

    The caller must ensure the annotator does not log, persist or send text.
    No callback is installed by default. A supplied label is one annotation,
    not independent validation; do not pass a model or API as the annotator.
    """
    if len(articles) > MAX_SAMPLES:
        raise ValueError("Description review exceeds the three-sample cap")
    reviews = []
    for index, article in enumerate(articles):
        if not isinstance(article, Article) or not all(
                isinstance(value, str) for value in (article.title, article.description)):
            raise ValueError("Description review requires normalized text fields")
        title, description = article.title, article.description
        too_long = len(title) > MAX_TITLE_CHARS or len(description) > MAX_DESCRIPTION_CHARS
        category, basis = Quality.UNCERTAIN, "unreviewed"
        # Check bounds before splitting, normalizing or invoking external code.
        words = 0 if too_long else len(description.split())
        if too_long:
            basis = "bounds_check"
        elif not description.strip():
            category, basis = Quality.MISSING, "rule"
        elif (re.findall(r"\w+", title.casefold()) and
              re.findall(r"\w+", title.casefold()) == re.findall(r"\w+", description.casefold())):
            category, basis = Quality.REPETITION, "rule"
        elif annotator is not None:
            try:
                category = annotator(title, description)
                if not isinstance(category, Quality):
                    raise ValueError
            except Exception:
                raise ValueError("Description annotator failed; no text retained") from None
            basis = "provided_annotator"
        reviews.append(DescriptionReview(index, category, basis, len(title), len(description),
                                         words, too_long))
    return tuple(reviews)
