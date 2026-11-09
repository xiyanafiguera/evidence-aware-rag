"""Extract structured signals from a query: document IDs, customers, dates and intent.

Deliberately rule-based and driven by `data/domain_rules.json`: the point of the prototype is to
make every decision traceable, not to hide it in a model.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date

from evidence_aware_rag.corpus import Corpus
from evidence_aware_rag.models import DateMention

DOC_ID = re.compile(r"\b([A-Z]{2,4}-\d{3})\b", re.IGNORECASE)
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS |= {name.lower(): i for i, name in enumerate(calendar.month_abbr) if name}
MONTH = "(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?"
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
MONTH_DAY_YEAR = re.compile(rf"\b{MONTH}\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.IGNORECASE)
DAY_MONTH_YEAR = re.compile(rf"\b(\d{{1,2}})\s+{MONTH},?\s+(\d{{4}})\b", re.IGNORECASE)
MONTH_YEAR = re.compile(rf"\b{MONTH},?\s+(\d{{4}})\b", re.IGNORECASE)
QUARTER = re.compile(r"\bQ([1-4])\s+(\d{4})\b", re.IGNORECASE)


def mentions(text: str, keyword: str) -> bool:
    """Whole-word (or whole-phrase) match, case-insensitive."""
    return re.search(rf"(?<!\w){re.escape(keyword.lower())}(?!\w)", text.lower()) is not None


def month_range(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def extract_dates(text: str) -> list[DateMention]:
    """Dates cited in the text. Month- or quarter-level mentions carry an `end` date."""
    found: list[DateMention] = []
    consumed: list[tuple[int, int]] = []

    def add(match: re.Match, day: date, end: date | None = None) -> None:
        if any(a <= match.start() < b for a, b in consumed):
            return
        consumed.append(match.span())
        found.append(DateMention(day=day, end=end, source="question", detail=match.group(0)))

    for m in ISO_DATE.finditer(text):
        add(m, date(int(m[1]), int(m[2]), int(m[3])))
    for m in MONTH_DAY_YEAR.finditer(text):
        add(m, date(int(m[3]), MONTHS[m[1].lower()], int(m[2])))
    for m in DAY_MONTH_YEAR.finditer(text):
        add(m, date(int(m[3]), MONTHS[m[2].lower()], int(m[1])))
    for m in MONTH_YEAR.finditer(text):
        add(m, *month_range(int(m[2]), MONTHS[m[1].lower()]))
    for m in QUARTER.finditer(text):
        first_month = (int(m[1]) - 1) * 3 + 1
        add(m, month_range(int(m[2]), first_month)[0], month_range(int(m[2]), first_month + 2)[1])
    return sorted(found, key=lambda d: d.day)


@dataclass
class QueryAnalysis:
    query: str
    doc_ids: list[str] = field(default_factory=list)  # IDs written in the query that exist
    customer_ids: list[str] = field(default_factory=list)  # named customers, then customers of cited docs
    dates: list[DateMention] = field(default_factory=list)
    intent: str | None = None


class QueryAnalyzer:
    def __init__(self, corpus: Corpus):
        self.corpus = corpus

    def analyze(self, query: str) -> QueryAnalysis:
        doc_ids = list(dict.fromkeys(m.upper() for m in DOC_ID.findall(query) if m.upper() in self.corpus))

        customers = [cid for name, cid in self.corpus.entity_aliases.items() if mentions(query, name)]
        for doc_id in doc_ids:
            customers += self.corpus.meta(doc_id).customer_ids
        customers = list(dict.fromkeys(customers))

        return QueryAnalysis(
            query=query,
            doc_ids=doc_ids,
            customer_ids=customers,
            dates=extract_dates(query),
            intent=self._intent(query, customers),
        )

    def _intent(self, query: str, customers: list[str]) -> str | None:
        # An intent about a specific case needs a concrete subject; without one, "credit" in a
        # general policy question would be mistaken for a compensation claim.
        if not customers:
            return None
        for name, rules in self.corpus.rules.intents.items():
            if any(mentions(query, kw) for kw in rules.keywords):
                return name
        return None
