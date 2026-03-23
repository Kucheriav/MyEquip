from sqlalchemy.orm import Session
from app.models import Breakdown
from app.schemas.breakdown_schema import BreakdownCreate, BreakdownUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class BreakdownCRUD(BaseCRUD[Breakdown, BreakdownCreate, BreakdownUpdate]):
    def __init__(self):
        super().__init__(Breakdown)

    def get_by_item(self, db: Session, item_id: int) -> List[Breakdown]:
        return db.query(Breakdown).filter(Breakdown.item_id == item_id).all()

    def get_unrepaired(self, db: Session) -> List[Breakdown]:
        return db.query(Breakdown).filter(Breakdown.repaired_date == None).all()


breakdown_crud = BreakdownCRUD()