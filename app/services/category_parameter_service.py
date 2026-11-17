"""Category properties: which parameters (name + type) describe items of
a category. A category inherits all parameters of its parent chain.

Parameter values are stored per item in item_parameter_values
(value_id for a predefined value, custom_value for free input).
"""
from typing import List

from sqlalchemy.orm import Session

from app.models import Category, Parameter
from app.schemas.parameter_schema import ParameterResponse
from app.services.exceptions import BusinessRuleError


def get_effective_parameters(
    db: Session,
    category: Category,
    include_inherited: bool = True,
) -> List[dict]:
    """Return [{id, name, param_type, inherited}...] for a category.

    Walks the parent chain (up to the root) when include_inherited is
    set; duplicates (same id) are reported once, owned by the child.
    """
    categories = [category]
    if include_inherited:
        current = category
        seen_ids = {current.id}
        while current.parent_id is not None and current.parent_id not in seen_ids:
            parent = db.query(Category).get(current.parent_id)
            if parent is None:
                break
            categories.append(parent)
            seen_ids.add(parent.id)
            current = parent

    result: List[dict] = []
    seen_parameter_ids = set()
    for level, cat in enumerate(categories):
        for parameter in sorted(cat.parameters, key=lambda p: p.name.lower()):
            if parameter.id in seen_parameter_ids:
                continue
            seen_parameter_ids.add(parameter.id)
            result.append({
                "id": parameter.id,
                "name": parameter.name,
                "param_type": parameter.param_type,
                "inherited": level > 0,
            })
    return result


def attach_parameter(db: Session, category_id: int, parameter_id: int) -> Parameter:
    category = db.query(Category).get(category_id)
    if category is None:
        raise BusinessRuleError("Category not found")
    parameter = db.query(Parameter).get(parameter_id)
    if parameter is None:
        raise BusinessRuleError("Parameter not found")
    if parameter in category.parameters:
        raise BusinessRuleError("Parameter is already attached to this category")
    category.parameters.append(parameter)
    db.add(category)
    db.commit()
    return parameter


def detach_parameter(db: Session, category_id: int, parameter_id: int) -> None:
    category = db.query(Category).get(category_id)
    if category is None:
        raise BusinessRuleError("Category not found")
    parameter = db.query(Parameter).get(parameter_id)
    if parameter is None or parameter not in category.parameters:
        raise BusinessRuleError("Parameter is not attached to this category")
    category.parameters.remove(parameter)
    db.add(category)
    db.commit()
