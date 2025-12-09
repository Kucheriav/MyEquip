from app.cruds.base_crud import BaseCRUD
from app.models.item_model import Item
import logging

logger = logging.getLogger("app.item_crud")


class ItemCRUD(BaseCRUD):
    model = Item


item_crud = ItemCRUD()