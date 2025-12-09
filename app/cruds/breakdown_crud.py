from app.cruds.base_crud import BaseCRUD
from app.models.breakdown_model import Breakdown
import logging

logger = logging.getLogger("app.breakdown_crud")


class BreakdownCRUD(BaseCRUD):
    model = Breakdown


breakdown_crud = BreakdownCRUD()