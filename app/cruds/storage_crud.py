from app.cruds.base_crud import BaseCRUD
from app.models.storage_model import Storage
import logging

logger = logging.getLogger("app.storage_crud")


class StorageCRUD(BaseCRUD):
    model = Storage


storage_crud = StorageCRUD()