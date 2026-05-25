"""Data access layer — repository pattern implementations."""

from app.repositories.base import BaseRepository
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.repositories.news_repository import NewsRepository

__all__ = ["BaseRepository", "ExchangeRateRepository", "NewsRepository"]
