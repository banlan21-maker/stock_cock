from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# --- News ---
class StockMention(BaseModel):
    stock_code: str
    stock_name: str
    reason: str


class NewsArticle(BaseModel):
    id: str
    title: str
    source: str
    url: str | None = None
    published_at: str
    category: str  # global / domestic / policy
    ai_summary: str | None = None
    related_stocks: list[StockMention] = []


class NewsListResponse(BaseModel):
    items: list[NewsArticle]
    total: int
    page: int
    limit: int


# --- Policy ---
class StockRecommendation(BaseModel):
    stock_code: str
    stock_name: str
    reason: str
    impact: str  # positive / negative / neutral


class PolicyInfo(BaseModel):
    id: str
    title: str
    department: str
    description: str
    effective_date: str | None = None
    ai_analysis: str | None = None
    beneficiary_stocks: list[StockRecommendation] = []
    created_at: str | None = None


class PolicyListResponse(BaseModel):
    items: list[PolicyInfo]
    total: int
    page: int
    limit: int


# --- Stock ---
class StockPrice(BaseModel):
    code: str
    name: str
    current_price: float
    change: float
    change_rate: float
    volume: int
    high: float
    low: float


class ChartDataPoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChartResponse(BaseModel):
    code: str
    name: str
    period: str
    data: list[ChartDataPoint]


class AnalysisItem(BaseModel):
    label: str
    result: str
    reason: str
    description: str


class StockAnalysis(BaseModel):
    stock_code: str
    stock_name: str
    sentiment: str  # bullish / bearish / neutral
    items: list[AnalysisItem]
    overall_score: int
    overall_comment: str
    analyzed_at: str
    expires_at: str | None = None


class StockSearchResult(BaseModel):
    code: str
    name: str
    market: str  # KOSPI / KOSDAQ


# --- Dashboard ---
class MarketIndex(BaseModel):
    value: float
    change_rate: float


class ThemeStock(BaseModel):
    code: str
    name: str
    change_rate: float
    volume: int


class ThemeGroup(BaseModel):
    theme: str
    avg_change_rate: float
    total_volume: int
    stocks: list[ThemeStock]


class ThemeTrendResponse(BaseModel):
    groups: list[ThemeGroup]
    trade_date: str
    period: str  # daily / weekly


class KeywordStock(BaseModel):
    code: str
    name: str
    market: str
    current_price: float | None = None
    change_rate: float | None = None
    reason: str


class KeywordFeedResponse(BaseModel):
    stocks: list[KeywordStock]
    news: list[NewsArticle]
    policies: list[PolicyInfo]


class DashboardResponse(BaseModel):
    top_news: list[NewsArticle]
    hot_policies: list[PolicyInfo]
    market_summary: dict[str, MarketIndex]


# --- Common ---
class ErrorResponse(BaseModel):
    error: dict
