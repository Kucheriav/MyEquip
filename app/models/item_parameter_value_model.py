from sqlalchemy import Column, Integer, String, ForeignKey,Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class ItemParameterValue(Base):
    __tablename__ = "item_parameter_values"
    item_id = Column(Integer, ForeignKey('items.id'), primary_key=True)
    parameter_id = Column(Integer, ForeignKey('parameters.id'), primary_key=True)
    value_str = Column(String)
    value_int = Column(Integer)
    value_bool = Column(Boolean)
    item = relationship("Item", back_populates="parameter_values")
    parameter = relationship("Parameter")