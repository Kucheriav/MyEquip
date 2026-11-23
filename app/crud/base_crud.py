from sqlalchemy.ext.asyncio import AsyncSession
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base CRUD operations for all models"""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        """Create a new object"""
        db_obj = self.model(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[ModelType]:
        """Get object by ID"""
        from sqlalchemy import select
        result = await db.execute(select(self.model).filter(self.model.id == obj_id))
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all objects with pagination"""
        from sqlalchemy import select
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """Update an object"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        """Delete an object"""
        db_obj = await self.get(db, obj_id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
            return True
        return False

    async def get_by_field(self, db: AsyncSession, field_name: str, value: Any) -> Optional[ModelType]:
        """Get object by any field"""
        from sqlalchemy import select
        result = await db.execute(select(self.model).filter(
            getattr(self.model, field_name) == value
        ))
        return result.scalar_one_or_none()