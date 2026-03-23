from sqlalchemy import Column, Integer, String, Date, Enum
from sqlalchemy.orm import relationship

from app.database import Base


class Parameter(Base):
    __tablename__ = "parameters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    param_type = Column(Enum('int', 'bool', 'str', name="param_type_enum"), nullable=False)
    values = relationship("Value", back_populates="parameter")
    categories = relationship("Parameter", back_populates="parameter")