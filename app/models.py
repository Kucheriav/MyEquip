from sqlalchemy import Column, Integer, String, JSON
from .database import Base

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    template = Column(String)
    properties = Column(JSON)  # динамические поля

class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    contact = Column(String)
    history = Column(JSON)