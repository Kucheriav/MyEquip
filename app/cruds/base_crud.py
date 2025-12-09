"""
Generic base CRUD class for async SQLAlchemy models with overrideable hooks.

Usage:
- Subclass BaseCRUD and set `model` to your SQLAlchemy model class.
- Optionally override any of the hook methods (pre_build_instance, build_instance,
  pre_commit, post_commit, pre_patch, validate_patch, apply_patch, pre_delete,
  serialize_instance) to change behavior for the subclass.

The connection decorator is preserved: methods accept `session` as the last argument,
so they can be used with the existing @connection decorator used across the project.
"""
from typing import Any, Dict, Optional, Type, TypeVar
from sqlalchemy.future import select
from sqlalchemy import func
import logging

from app.errors_custom_types import *  # NotFoundError, UpdateError, etc.
from app.database import connection

T = TypeVar("T")

logger = logging.getLogger("app.base_crud")
FORBIDDEN_FIELDS = {"id", "created_at", "updated_at"}


class BaseCRUD:
    # Subclasses should set this
    model: Optional[Type[Any]] = None
    # Subclasses may override forbidden fields set
    forbidden_fields = FORBIDDEN_FIELDS

    def __init_subclass__(cls, **kwargs):
        # Give each subclass its own logger name automatically
        super().__init_subclass__(**kwargs)
        name = getattr(cls, "model", None)
        cls.logger = logging.getLogger(f"app.{cls.__name__.lower()}")
        if cls.model is None:
            cls.logger.warning("Subclass of BaseCRUD created without setting `model` attribute")

    # ---------- Hooks (override these in subclasses as needed) ----------
    async def pre_build_instance(self, payload: Any, session) -> Any:
        """
        Override to modify/validate payload before building model instance.
        Return possibly modified payload.
        """
        return payload

    def build_instance(self, payload: Any) -> Any:
        """
        Create model instance from payload. Default assumes payload has `.dict()` method
        (pydantic model). Override if you need special construction.
        """
        if hasattr(payload, "dict"):
            return self.model(**payload.dict())
        elif isinstance(payload, dict):
            return self.model(**payload)
        else:
            # Last resort: try to pass it directly
            return self.model(payload)

    async def pre_commit(self, instance: Any, session):
        """
        Hook before commit. Can be used to mutate instance or perform side effects.
        """
        return

    async def post_commit(self, instance: Any, session):
        """
        Hook after commit and refresh. Useful to run extra queries or publish events.
        """
        return

    async def pre_patch(self, obj: Any, key: str, value: Any, session) -> Any:
        """
        Hook before applying a single patch field.
        Return possibly transformed value.
        """
        return value

    async def validate_patch(self, obj: Any, key: str, value: Any, session):
        """
        Hook to validate a patch operation. Raise if invalid.
        """
        return

    async def apply_patch(self, obj: Any, key: str, value: Any, session):
        """
        Default application: setattr. Override if you need special logic (e.g., relationships).
        """
        setattr(obj, key, value)

    async def pre_delete(self, obj: Any, session):
        """
        Hook before deletion. Can raise to prevent deletion.
        """
        return

    def serialize_instance(self, instance: Any) -> Dict[str, Any]:
        """
        By default, returns instance.__dict__.
        Override if you want to exclude private fields or convert relationships.
        """
        try:
            return {k: v for k, v in instance.__dict__.items() if not k.startswith("_")}
        except Exception:
            return {}

    # ---------- CRUD operations ----------
    @connection
    async def create(self, payload: Any, session):
        """
        Generic create. `payload` is typically a pydantic schema instance.
        """
        self.logger.info(f"Creating a new {self.model.__name__} entry")
        try:
            payload = await self.pre_build_instance(payload, session)
            instance = self.build_instance(payload)
            session.add(instance)
            await self.pre_commit(instance, session)
            await session.commit()
            await session.refresh(instance)
            await self.post_commit(instance, session)
            self.logger.info(f"{self.model.__name__} created successfully with ID: {getattr(instance, 'id', None)}")
            return instance
        except Exception:
            self.logger.exception(f"Error occurred while creating {self.model.__name__}")
            raise

    @connection
    async def get(self, obj_id: int, session):
        """
        Generic get by primary key.
        """
        self.logger.info(f"Fetching {self.model.__name__} with ID: {obj_id}")
        try:
            obj = await session.get(self.model, obj_id)
            if obj is None:
                self.logger.warning(f"{self.model.__name__} with ID {obj_id} not found")
                raise NotFoundError(self.model.__name__, obj_id)
            self.logger.info(f"{self.model.__name__} with ID {obj_id} retrieved successfully")
            return obj
        except Exception:
            self.logger.exception(f"Error occurred while fetching {self.model.__name__} with ID {obj_id}")
            raise

    @connection
    async def get_paginated(self, page: int = 1, page_size: int = 10, session=None):
        """
        Generic paginated list.
        """
        self.logger.info(f"Fetching paginated {self.model.__name__}s: Page {page}, Page Size {page_size}")
        try:
            offset = (page - 1) * page_size
            query = select(self.model).offset(offset).limit(page_size)
            result = await session.execute(query)
            items = result.scalars().all()
            total_items_query = await session.execute(select(func.count(self.model.id)))
            total_items = total_items_query.scalar()
            total_pages = (total_items + page_size - 1) // page_size if total_items is not None else 0
            response = {
                "page": page,
                "page_size": page_size,
                "total_items": total_items or 0,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                f"{self.model.__name__.lower()}s": [self.serialize_instance(i) for i in items] if items else []
            }
            self.logger.info(f"Paginated {self.model.__name__}s retrieved successfully: Page {page}")
            return response
        except Exception:
            self.logger.exception(f"Error occurred while fetching paginated {self.model.__name__}s")
            raise

    @connection
    async def patch(self, obj_id: int, session, params):
        """
        Generic patch. `params` expected to have `.params` dict like in your sample.
        """
        try:
            obj = await session.get(self.model, obj_id)
            if obj is None:
                self.logger.warning(f"{self.model.__name__} with ID {obj_id} not found")
                raise NotFoundError(self.model.__name__, obj_id)

            for key, value in params.params.items():
                if not hasattr(obj, key):
                    self.logger.warning(f"Field {key} not found in {self.model.__name__} model")
                    raise UpdateError(self.model.__name__, obj_id)

                if key in self.forbidden_fields:
                    self.logger.warning(f"Attempt to patch forbidden field {key} for {self.model.__name__} ID {obj_id}")
                    continue

                # validate and transform
                await self.validate_patch(obj, key, value, session)
                new_value = await self.pre_patch(obj, key, value, session)
                await self.apply_patch(obj, key, new_value, session)

            await session.commit()
            await session.refresh(obj)
            self.logger.info(f"{self.model.__name__} with ID {obj_id} patched successfully")
            return obj
        except Exception:
            self.logger.exception(f"Error occurred while patching {self.model.__name__} with ID {obj_id}")
            raise

    @connection
    async def delete(self, obj_id: int, session):
        """
        Generic delete.
        """
        self.logger.info(f"Deleting {self.model.__name__} with ID: {obj_id}")
        try:
            obj = await session.get(self.model, obj_id)
            if obj is None:
                self.logger.warning(f"{self.model.__name__} with ID {obj_id} not found")
                raise NotFoundError(self.model.__name__, obj_id)

            await self.pre_delete(obj, session)
            await session.delete(obj)
            await session.commit()
            self.logger.info(f"{self.model.__name__} with ID {obj_id} deleted successfully")
            return True
        except Exception:
            self.logger.exception(f"Error occurred while deleting {self.model.__name__} with ID {obj_id}")
            raise