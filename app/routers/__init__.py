from sqlalchemy.orm import Session
from app.models import ItemParameterValue
from app.schemas.item_parameter_value_schema import (
    ItemParameterValueCreate, ItemParameterValueResponse
)
from app.crud.base_crud import BaseCRUD
from typing import List


class ItemParameterValueCRUD(BaseCRUD[ItemParameterValue, ItemParameterValueCreate, ItemParameterValueResponse]):
    def __init__(self):
        super().__init__(ItemParameterValue)

    def get_by_item(self, db: Session, item_id: int) -> List[ItemParameterValue]:
        return db.query(ItemParameterValue).filter(
            ItemParameterValue.item_id == item_id
        ).all()

    def get_by_parameter(self, db: Session, parameter_id: int) -> List[ItemParameterValue]:
        return db.query(ItemParameterValue).filter(
            ItemParameterValue.parameter_id == parameter_id
        ).all()


item_parameter_value_crud = ItemParameterValueCRUD()