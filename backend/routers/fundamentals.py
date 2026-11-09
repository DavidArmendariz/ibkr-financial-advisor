import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.fundamentals.service import FundamentalsError, fundamentals_service

router = APIRouter()

ARTICLE_PART = re.compile(r"^[A-Za-z0-9$:._\-]{1,80}$")


def _error(e: FundamentalsError) -> JSONResponse:
    return JSONResponse(status_code=e.status, content={"detail": e.message, "code": e.code})


@router.get("/article/{provider}/{article_id}")
async def get_article(provider: str, article_id: str):
    if not ARTICLE_PART.match(provider) or not ARTICLE_PART.match(article_id):
        raise HTTPException(status_code=422, detail="Invalid article")
    try:
        text = await fundamentals_service.article(provider, article_id)
    except FundamentalsError as e:
        return _error(e)
    return {"text": text}


@router.get("/{ticker}")
async def get_fundamentals(ticker: str, refresh: bool = False):
    try:
        return await fundamentals_service.lookup(ticker, refresh)
    except FundamentalsError as e:
        return _error(e)


@router.post("/{ticker}/analysis")
async def write_analysis(ticker: str):
    try:
        return await fundamentals_service.analyze(ticker)
    except FundamentalsError as e:
        return _error(e)
