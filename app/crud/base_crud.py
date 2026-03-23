from sqlalchemy.orm import Session
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base CRUD operations for all models"""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        """Create a new object"""
        db_obj = self.model(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, obj_id: int) -> Optional[ModelType]:
        """Get object by ID"""
        return db.query(self.model).filter(self.model.id == obj_id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all objects with pagination"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def update(self, db: Session, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """Update an object"""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, obj_id: int) -> bool:
        """Delete an object"""
        db_obj = self.get(db, obj_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False

    def get_by_field(self, db: Session, field_name: str, value: Any) -> Optional[ModelType]:
        """Get object by any field"""
        return db.query(self.model).filter(
            getattr(self.model, field_name) == value
        ).first()