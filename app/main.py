from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging


logger = logging.getLogger(__name__)
logger.info("FastAPI starting...")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)