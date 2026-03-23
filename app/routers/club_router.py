from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import ClubCRUD
from app.schemas.club_schema import ClubCreate, ClubUpdate, ClubResponse
from typing import List

router = APIRouter(prefix="/api/clubs", tags=["clubs"])
club_crud = ClubCRUD()


@router.post("/", response_model=ClubResponse, status_code=201)
def create_club(club: ClubCreate, db: Session = Depends(get_db)):
    """Create a new club"""
    db_club = club_crud.get_by_name(db, name=club.name)
    if db_club:
        raise HTTPException(status_code=400, detail="Club already exists")
    return club_crud.create(db, obj_in=club)


@router.get("/{club_id}", response_model=ClubResponse)
def get_club(club_id: int, db: Session = Depends(get_db)):
    """Get club by ID"""
    club = club_crud.get(db, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club


@router.get("/", response_model=List[ClubResponse])
def get_all_clubs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all clubs"""
    return club_crud.get_all(db, skip=skip, limit=limit)


@router.put("/{club_id}", response_model=ClubResponse)
def update_club(club_id: int, club_update: ClubUpdate, db: Session = Depends(get_db)):
    """Update club"""
    db_club = club_crud.get(db, club_id)
    if not db_club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club_crud.update(db, db_obj=db_club, obj_in=club_update)


@router.delete("/{club_id}", status_code=204)
def delete_club(club_id: int, db: Session = Depends(get_db)):
    """Delete club"""
    if not club_crud.delete(db, club_id):
        raise HTTPException(status_code=404, detail="Club not found")
    return None