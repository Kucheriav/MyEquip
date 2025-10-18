from . import models, database

def get_items(db):
    return db.query(models.Item).all()

def create_item(db, item):
    db_item = models.Item(name=item.name, template=item.template, properties=item.properties)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item