from sqlalchemy.orm import Session
from app.models import Parameter
from app.schemas.parameter_schema import ParameterCreate, ParameterUpdate
from app.crud.base_crud import BaseCRUD


class ParameterCRUD(BaseCRUD[Parameter, ParameterCreate, ParameterUpdate]):
    def __init__(self):
        super().__init__(Parameter)

    def get_by_name(self, db: Session, name: str) -> Parameter:
        return db.query(Parameter).filter(Parameter.name == name).first()


parameter_crud = ParameterCRUD()