from app.cruds.base_crud import BaseCRUD
from app.models.category_model import Category
import logging

logger = logging.getLogger("app.category_crud")


class CategoryCRUD(BaseCRUD):
    model = Category


category_crud = CategoryCRUD()