from sqlalchemy.orm import Session
from app.models import User
from app.schemas.user_schema import UserCreate, UserUpdate
from app.crud.base_crud import BaseCRUD


class UserCRUD(BaseCRUD[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(User)

    def get_by_email(self, db: Session, email: str) -> User:
        # An empty email means "no email set". Without this guard
        # `User.email == None` renders `email IS NULL` and matches any
        # user without an email (e.g. the very user being created).
        if not email:
            return None
        return db.query(User).filter(User.email == email).first()

    def get_by_phone(self, db: Session, phone: str) -> User:
        return db.query(User).filter(User.phone == phone).first()

    def get_by_club(self, db: Session, club_id: int):
        return db.query(User).join(User.clubs).filter(
            User.clubs.any(id=club_id)
        ).all()


user_crud = UserCRUD()