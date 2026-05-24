"""Generic repository base class."""

from app.core.database import Base
from sqlalchemy.orm import Session
from typing import Generic, TypeVar

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Abstract base repository for CRUD operations (to be extended per entity)."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    @property
    def session(self) -> Session:
        return self._session

    def get_by_id(self, entity_id: int) -> ModelT | None:
        return self._session.get(self._model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        self._session.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        self._session.delete(entity)
        self._session.flush()
