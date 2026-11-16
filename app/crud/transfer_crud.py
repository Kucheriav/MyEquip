from sqlalchemy.orm import Session
from app.models import Transfer
from app.schemas.transfer_schema import TransferCreate
from app.crud.base_crud import BaseCRUD
from typing import List


class TransferCRUD(BaseCRUD[Transfer, TransferCreate, TransferCreate]):
    def __init__(self):
        super().__init__(Transfer)

    def get_by_item(self, db: Session, item_id: int) -> List[Transfer]:
        return db.query(Transfer).filter(Transfer.item_id == item_id).all()

    def get_by_from_storage(self, db: Session, storage_id: int) -> List[Transfer]:
        return db.query(Transfer).filter(Transfer.from_storage_id == storage_id).all()

    def get_by_to_storage(self, db: Session, storage_id: int) -> List[Transfer]:
        return db.query(Transfer).filter(Transfer.to_storage_id == storage_id).all()


transfer_crud = TransferCRUD()
