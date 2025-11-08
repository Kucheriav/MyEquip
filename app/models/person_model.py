from sqlalchemy import Column, Integer, String, JSON
from app.database import Base


class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    contact = Column(String)
    history = Column(JSON)