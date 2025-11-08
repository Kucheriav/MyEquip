from app.models.item_model import Item
from app import database





def get_items(db):
    return db.query(Item).all()

def create_item(db, item):
    db_item = Item(name=item.name, template=item.template, properties=item.properties)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item