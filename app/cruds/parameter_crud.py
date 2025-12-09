from app.cruds.base_crud import BaseCRUD
from app.models.parameter_model import Parameter
import logging

logger = logging.getLogger("app.parameter_crud")


class ParameterCRUD(BaseCRUD):
    model = Parameter


parameter_crud = ParameterCRUD()