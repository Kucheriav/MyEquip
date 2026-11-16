from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ItemParameterValue(Base):
    __tablename__ = "item_parameter_values"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    parameter_id = Column(Integer, ForeignKey('parameters.id'), nullable=False)
    value_id = Column(Integer, ForeignKey('values.id'), nullable=True)
    custom_value = Column(String(200), nullable=True)  # For custom values not in predefined list

    # Relationships
    item = relationship("Item", back_populates="parameters")
    parameter = relationship("Parameter", back_populates="item_values")
    value = relationship("Value")