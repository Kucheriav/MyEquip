from sqlalchemy.orm import Session
from app.models import Storage
from app.schemas.storage_schema import StorageCreate, StorageUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class StorageCRUD(BaseCRUD[Storage, StorageCreate, StorageUpdate]):
    def __init__(self):
        super().__init__(Storage)

    def get_by_club(self, db: Session, club_id: int) -> List[Storage]:
        return db.query(Storage).filter(Storage.club_id == club_id).all()


storage_crud = StorageCRUD()