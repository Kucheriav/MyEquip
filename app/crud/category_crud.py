from sqlalchemy.orm import Session
from app.models import Category
from app.schemas.category_schema import CategoryCreate, CategoryUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class CategoryCRUD(BaseCRUD[Category, CategoryCreate, CategoryUpdate]):
    def __init__(self):
        super().__init__(Category)

    def get_by_club(self, db: Session, club_id: int) -> List[Category]:
        return db.query(Category).filter(Category.club_id == club_id).all()

    def get_root_categories(self, db: Session, club_id: int) -> List[Category]:
        return db.query(Category).filter(
            Category.club_id == club_id,
            Category.parent_id == None
        ).all()


category_crud = CategoryCRUD()