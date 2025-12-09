from app.cruds.base_crud import BaseCRUD
from app.models.user_model import User
from app.schemas.user_schema import UserCreate
import logging
from passlib.hash import bcrypt  # если в проекте используется passlib

logger = logging.getLogger("app.user_crud")


class UserCRUD(BaseCRUD):
    model = User
    forbidden_fields = {"id", "created_at", "updated_at", "password"}

    async def pre_build_instance(self, payload: UserCreate, session):
        data = payload.dict()
        pwd = data.get("password")
        if pwd:
            data["password"] = bcrypt.hash(pwd)
        return data

    async def pre_patch(self, obj, key, value, session):
        if key == "password" and value:
            return bcrypt.hash(value)
        return value

    def serialize_instance(self, instance):
        data = super().serialize_instance(instance)
        data.pop("password", None)
        return data


user_crud = UserCRUD()