from app.cruds.base_crud import BaseCRUD
from app.models.item_parameter_value_model import ItemParameterValue
import logging

logger = logging.getLogger("app.item_parameter_value_crud")


class ItemParameterValueCRUD(BaseCRUD):
    model = ItemParameterValue


item_parameter_value_crud = ItemParameterValueCRUD()