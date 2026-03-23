from sqlalchemy.orm import Session
from app.models import Value
from app.schemas.value_schema import ValueCreate, ValueUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class ValueCRUD(BaseCRUD[Value, ValueCreate, ValueUpdate]):
    def __init__(self):
        super().__init__(Value)

    def get_by_parameter(self, db: Session, parameter_id: int) -> List[Value]:
        return db.query(Value).filter(Value.parameter_id == parameter_id).all()


value_crud = ValueCRUD()