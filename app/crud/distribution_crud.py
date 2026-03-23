from sqlalchemy.orm import Session
from app.models import Distribution
from app.schemas.distribution_schema import DistributionCreate, DistributionUpdate
from app.crud.base_crud import BaseCRUD
from typing import List
from datetime import date


class DistributionCRUD(BaseCRUD[Distribution, DistributionCreate, DistributionUpdate]):
    def __init__(self):
        super().__init__(Distribution)

    def get_by_item(self, db: Session, item_id: int) -> List[Distribution]:
        return db.query(Distribution).filter(Distribution.item_id == item_id).all()

    def get_by_user_given(self, db: Session, user_id: int) -> List[Distribution]:
        return db.query(Distribution).filter(Distribution.giver_id == user_id).all()

    def get_by_user_received(self, db: Session, user_id: int) -> List[Distribution]:
        return db.query(Distribution).filter(Distribution.getter_id == user_id).all()

    def get_active_distributions(self, db: Session) -> List[Distribution]:
        return db.query(Distribution).filter(
            Distribution.status == 'issued'
        ).all()

    def get_overdue_distributions(self, db: Session, today: date) -> List[Distribution]:
        return db.query(Distribution).filter(
            Distribution.status == 'issued',
            Distribution.expiration_date < today
        ).all()


distribution_crud = DistributionCRUD()