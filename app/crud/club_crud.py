from sqlalchemy.orm import Session
from app.models import Club, ClubMember
from app.schemas.club_schema import ClubCreate, ClubUpdate
from app.crud.base_crud import BaseCRUD


class ClubCRUD(BaseCRUD[Club, ClubCreate, ClubUpdate]):
    def __init__(self):
        super().__init__(Club)

    def get_by_name(self, db: Session, name: str) -> Club:
        return db.query(Club).filter(Club.name == name).first()

    def get_by_member(self, db: Session, user_id: int):
        """Clubs the user belongs to in any role."""
        return (
            db.query(Club)
            .join(ClubMember, ClubMember.club_id == Club.id)
            .filter(ClubMember.user_id == user_id)
            .order_by(Club.id)
            .all()
        )


club_crud = ClubCRUD()
