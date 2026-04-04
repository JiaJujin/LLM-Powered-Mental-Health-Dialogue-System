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

    try:
        result = await agent.select_role(req.body_feeling, req.need, req.emotion)
        role = result.get("role", "Emotional Support")
        confidence = float(result.get("confidence", 0.8))
        reasons = result.get("reasons", "")
    except Exception as e:
        print(f"[PRECHECK] LLM 调用失败，使用默认角色: {e}")
        role = "Emotional Support"
        confidence = 0.0
        reasons = "LLM 不可用，使用默认角色。"

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
