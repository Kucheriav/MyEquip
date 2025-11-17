from sqlalchemy import Column, Integer, String, Date, Enum
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    surname = Column(String)
    last_name = Column(String)
    date_of_birth = Column(Date)
    email = Column(Email)
    phone = Column(String, unique=True)
    pswd_hash = Column(String)
    status = Column(Enum('guest', 'unverified', 'full', name="user_status_enum"), nullable=False)
