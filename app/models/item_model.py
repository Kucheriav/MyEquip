from sqlalchemy import Column, Integer, String, JSON
from app.database import Base

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    properties = Column(JSON)