from fastapi import FastAPI
from . import models, database, crud, schemas
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

models.Base.metadata.create_all(bind=database.engine)

@app.get("/items/")
def list_items():
    return crud.get_items(database.get_db())

@app.post("/items/")
def create_item(item: schemas.ItemCreate):
    return crud.create_item(database.get_db(), item)