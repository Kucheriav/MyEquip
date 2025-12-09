from app.cruds.base_crud import BaseCRUD
from app.models.distribution_model import Distribution
import logging

logger = logging.getLogger("app.distribution_crud")


class DistributionCRUD(BaseCRUD):
    model = Distribution


distribution_crud = DistributionCRUD()