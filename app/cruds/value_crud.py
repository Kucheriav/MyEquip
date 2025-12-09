from app.cruds.base_crud import BaseCRUD
from app.models.value_model import Value
import logging

logger = logging.getLogger("app.value_crud")


class ValueCRUD(BaseCRUD):
    model = Value


value_crud = ValueCRUD()