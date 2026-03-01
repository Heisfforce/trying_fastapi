from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional

SQLALCHEMY_DATABASE_URL = "sqlite:///./notes.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class NoteModel(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(bind=engine)

class NoteBase(BaseModel):
    title: str
    content: str
    pinned: bool = False

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class NoteResponse(NoteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/notes", response_model=NoteResponse)
def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    db_note = NoteModel(**note.model_dump())
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

@app.get("/notes", response_model=List[NoteResponse])
def get_all_notes(db: Session = Depends(get_db)):
    return db.query(NoteModel).all()

@app.get("/notes/pinned", response_model=List[NoteResponse])
def get_pinned_notes(db: Session = Depends(get_db)):
    return db.query(NoteModel).filter(NoteModel.pinned == True).all()

@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_single_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.put("/notes/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, note_update: NoteUpdate, db: Session = Depends(get_db)):
    db_note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    update_data = note_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_note, key, value)
    
    db_note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_note)
    return db_note

@app.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    db_note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    db.delete(db_note)
    db.commit()
    return {"id": note_id, "message": "Deleted successfully"}

@app.patch("/notes/{note_id}/pinned", response_model=NoteResponse)
def toggle_pinned(note_id: int, db: Session = Depends(get_db)):
    db_note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    db_note.pinned = not db_note.pinned
    db_note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_note)
    return db_note