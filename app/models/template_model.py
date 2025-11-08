from sqlalchemy import Column, Integer, String, JSON
from app.database import Base


class Template(Base):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    properties = Column(JSON)  