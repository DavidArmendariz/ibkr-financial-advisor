import asyncio
import html
import re
from typing import Optional

from ib_async import Stock

from backend.services import ibkr_service

IBKR_HEADLINES = 30
MAX_HEADLINES = 40
REQUEST_TIMEOUT = 15
# IBKR headlines start with metadata such as {A:800015:L:en}.
PREFIX = re.compile(r"^\s*\{[^}]*\}\s*")
TAGS = re.compile(r"<[^>]+>")

_providers: dict[str, str] = {}


def strip_prefix(headline: str) -> str:
    return PREFIX.sub("", headline).strip()


def _key(headline: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", headline.lower()).strip()


def merge(*sources: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for item in sorted((i for s in sources for i in s), key=lambda i: i["time"], reverse=True):
        key = _key(item["headline"])
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out[:MAX_HEADLINES]


async def providers() -> dict[str, str]:
    if not _providers:
        found = await asyncio.wait_for(ibkr_service.ibkr.reqNewsProvidersAsync(), REQUEST_TIMEOUT)
        _providers.update({p.code: p.name for p in found or []})
    return _providers


async def ibkr_news(ticker: str) -> list[dict]:
    names = await providers()
    if not names:
        return []
    contract = Stock(ticker, "SMART", "USD")
    qualified = await asyncio.wait_for(ibkr_service.ibkr.qualifyContractsAsync(contract), REQUEST_TIMEOUT)
    if not qualified or not getattr(qualified[0], "conId", 0):
        return []
    items = await asyncio.wait_for(
        ibkr_service.ibkr.reqHistoricalNewsAsync(qualified[0].conId, "+".join(names), "", "", IBKR_HEADLINES), REQUEST_TIMEOUT
    )
    return [
        {
            "time": n.time.timestamp(),
            "source": names.get(n.providerCode, n.providerCode),
            "headline": strip_prefix(n.headline),
            "url": None,
            "provider": n.providerCode,
            "article_id": n.articleId,
        }
        for n in items or []
        if strip_prefix(n.headline)
    ]


def article_text(article_type: int, text: str) -> Optional[str]:
    # Type 1 is a binary (PDF) article, which the view can't show as text.
    if article_type != 0:
        return None
    plain = TAGS.sub(" ", re.sub(r"(?i)<br\s*/?>|</p>", "\n", text))
    lines = [re.sub(r"[ \t]+", " ", html.unescape(line)).strip() for line in plain.splitlines()]
    return "\n".join(line for line in lines if line)


async def ibkr_article(provider: str, article_id: str) -> Optional[str]:
    article = await asyncio.wait_for(ibkr_service.ibkr.reqNewsArticleAsync(provider, article_id), REQUEST_TIMEOUT)
    return article_text(article.articleType, article.articleText) if article else None
