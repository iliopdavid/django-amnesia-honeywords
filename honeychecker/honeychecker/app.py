from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
from sqlalchemy.exc import OperationalError

from .db import Base, engine, SessionLocal
from .models import HoneycheckerRecord

def init_db_with_retry(retries: int = 30, delay: float = 1.0) -> None:
    for i in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            time.sleep(delay)
    # last try (raise real error)
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="Honeychecker")

@app.on_event("startup")
def on_startup():
    init_db_with_retry()

class SetRequest(BaseModel):
    user_id: str
    real_index: int

class VerifyRequest(BaseModel):
    user_id: str
    candidate_index: int

@app.post("/set")
def set_real_index(req: SetRequest):
    db = SessionLocal()
    try:
        rec = db.get(HoneycheckerRecord, req.user_id)
        if rec is None:
            rec = HoneycheckerRecord(user_id=req.user_id, real_index=req.real_index)
            db.add(rec)
        else:
            rec.real_index = req.real_index
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()

@app.post("/verify")
def verify(req: VerifyRequest):
    db = SessionLocal()
    try:
        rec = db.get(HoneycheckerRecord, req.user_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {"is_real": req.candidate_index == rec.real_index}
    finally:
        db.close()