from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models, schemas
from ..therapy_agent import agent

router = APIRouter(tags=["precheck"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/precheck", response_model=schemas.PrecheckResponse)
async def precheck(req: schemas.PrecheckRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(anon_id=req.anon_id).first()
    if not user:
        user = models.User(anon_id=req.anon_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    result = await agent.select_role(req.body_feeling, req.need, req.emotion)
    role = result["role"]
    confidence = float(result.get("confidence", 0.8))
    reasons = result.get("reasons", "")

    pc = models.PreCheck(
        user_id=user.id,
        body_feeling=req.body_feeling,
        need=req.need,
        emotion=req.emotion,
        assigned_role=role,
    )
    db.add(pc)
    db.commit()

    return schemas.PrecheckResponse(role=role, confidence=confidence, reasons=reasons)
