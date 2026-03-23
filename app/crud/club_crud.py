from sqlalchemy.orm import Session
from app.models import Club
from app.schemas.club_schema import ClubCreate, ClubUpdate
from app.crud.base_crud import BaseCRUD


class ClubCRUD(BaseCRUD[Club, ClubCreate, ClubUpdate]):
    def __init__(self):
        super().__init__(Club)

    def get_by_name(self, db: Session, name: str) -> Club:
        return db.query(Club).filter(Club.name == name).first()


club_crud = ClubCRUD()