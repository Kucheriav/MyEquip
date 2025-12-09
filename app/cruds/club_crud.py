from app.cruds.base_crud import BaseCRUD
from app.models.club_model import Club
import logging

logger = logging.getLogger("app.club_crud")


class ClubCRUD(BaseCRUD):
    model = Club


club_crud = ClubCRUD()