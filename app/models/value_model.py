from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class Value(Base):
    __tablename__ = "values"
    id = Column(Integer, primary_key=True, index=True)
    value = Column(String)
    parameter_id = Column(Integer, ForeignKey('parameters.id'))
