from sqlalchemy.orm import Session
from app.models import Item
from app.schemas.item_schema import ItemCreate, ItemUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class ItemCRUD(BaseCRUD[Item, ItemCreate, ItemUpdate]):
    def __init__(self):
        super().__init__(Item)

    def get_by_storage(self, db: Session, storage_id: int) -> List[Item]:
        return db.query(Item).filter(Item.storage_id == storage_id).all()

    def get_by_owner(self, db: Session, owner_id: int) -> List[Item]:
        return db.query(Item).filter(Item.owner_id == owner_id).all()

    def get_by_category(self, db: Session, category_id: int) -> List[Item]:
        return db.query(Item).filter(Item.category_id == category_id).all()

    def get_by_status(self, db: Session, status: str) -> List[Item]:
        return db.query(Item).filter(Item.status == status).all()

    def get_by_serial_number(self, db: Session, serial_number: str) -> Item:
        return db.query(Item).filter(Item.serial_number == serial_number).first()


item_crud = ItemCRUD()