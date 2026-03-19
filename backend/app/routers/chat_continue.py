from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from ..database import SessionLocal
from .. import models, schemas
from ..therapy_agent import agent
from .journal import (
    render_b1_text,
    render_b2_text,
    render_b3_text,
    render_b1_followup_text,
    render_b2_followup_text,
    fallback_b1_followup,
    fallback_b2_followup,
    fallback_b2,
    fallback_b3,
    has_unsafe_flags,
)

router = APIRouter(tags=["chat"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_context(session: models.TherapySession) -> dict:
    """Build context dict from session data"""
    try:
        precheck = json.loads(session.precheck_context)
    except Exception:
        precheck = {
            "body": "Unknown",
            "need": "Unknown",
            "emotion": "Unknown",
            "assigned_role": "Emotional Support"
        }

    return {
        "assigned_role": session.selected_role or precheck.get("assigned_role", "Emotional Support"),
        "body": precheck.get("body", ""),
        "need": precheck.get("need", ""),
        "emotion": precheck.get("emotion", ""),
        "weekly_summary": "",
    }


def get_conversation_history(session: models.TherapySession) -> list:
    """Parse conversation history from session"""
    try:
        return json.loads(session.conversation_history)
    except Exception:
        return []


def format_conversation_for_llm(history: list) -> str:
    """Format conversation history as string for LLM prompts"""
    formatted = ""
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted += f"{role}: {content}\n"
    return formatted


@router.post("/chat/continue", response_model=schemas.ChatContinueResponse)
async def continue_chat(req: schemas.ChatContinueRequest, db: Session = Depends(get_db)):
    """Continue a therapy session with gating logic"""

    # Find session
    session = db.query(models.TherapySession).filter_by(session_id=req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if session is completed
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")

    # High risk check - stop therapy flow
    if session.risk_level >= 3:
        raise HTTPException(status_code=400, detail="High risk session - please seek professional help")

    # Get conversation history
    conversation_history = get_conversation_history(session)

    # Get context
    context = build_context(session)

    # Find last assistant message
    last_assistant_msg = None
    last_assistant_mode = None
    for msg in reversed(conversation_history):
        if msg.get("role") == "assistant":
            last_assistant_msg = msg.get("content", "")
            last_assistant_mode = msg.get("mode", "B1")
            break

    # Append user message
    conversation_history.append({
        "role": "user",
        "content": req.user_message
    })

    gating_decision = None
    new_assistant_msg = ""
    new_round_index = session.round_index

    try:
        if session.round_index == 1:
            # B1 stage - check if ready for B2
            gating_result = await agent.gate_b1_to_b2(
                journal_text=session.journal_text,
                assistant_b1=last_assistant_msg or "",
                user_reply=req.user_message
            )

            gating_decision = schemas.GatingDecision(
                decision=gating_result.get("decision", "STAY_IN_B1"),
                reason=gating_result.get("reason", ""),
                evidence=gating_result.get("evidence", []),
                followup_style=gating_result.get("followup_style", "情緒承接")
            )

            if gating_result.get("decision") == "READY_FOR_B2":
                # Generate B2
                conv_str = format_conversation_for_llm(conversation_history)
                b2_json = await agent.run_b2(context, conv_str, req.user_message)
                if has_unsafe_flags(b2_json):
                    b2_json = fallback_b2()

                new_assistant_msg = render_b2_text(b2_json)
                new_round_index = 2

                conversation_history.append({
                    "role": "assistant",
                    "content": new_assistant_msg,
                    "mode": "B2"
                })
            else:
                # Stay in B1 - generate follow-up
                followup_style = gating_result.get("followup_style", "情緒承接")
                b1_followup_json = await agent.run_b1_followup(
                    context=context,
                    journal_text=session.journal_text,
                    previous_b1=last_assistant_msg or "",
                    user_reply=req.user_message,
                    followup_style=followup_style
                )
                if has_unsafe_flags(b1_followup_json):
                    b1_followup_json = fallback_b1_followup()

                new_assistant_msg = render_b1_followup_text(b1_followup_json)
                # Stay in round 1

                conversation_history.append({
                    "role": "assistant",
                    "content": new_assistant_msg,
                    "mode": "B1"
                })

        elif session.round_index == 2:
            # B2 stage - check if ready for B3
            gating_result = await agent.gate_b2_to_b3(
                journal_text=session.journal_text,
                assistant_b2=last_assistant_msg or "",
                user_reply=req.user_message
            )

            gating_decision = schemas.GatingDecision(
                decision=gating_result.get("decision", "STAY_IN_B2"),
                reason=gating_result.get("reason", ""),
                evidence=gating_result.get("evidence", []),
                followup_style=gating_result.get("followup_style", "澄清自動想法")
            )

            if gating_result.get("decision") == "READY_FOR_B3":
                # Generate B3
                conv_str = format_conversation_for_llm(conversation_history)
                b3_json = await agent.run_b3(context, conv_str, req.user_message)
                if has_unsafe_flags(b3_json):
                    b3_json = fallback_b3()

                new_assistant_msg = render_b3_text(b3_json)
                new_round_index = 3

                conversation_history.append({
                    "role": "assistant",
                    "content": new_assistant_msg,
                    "mode": "B3"
                })

                # Mark session as completed
                session.status = "completed"
            else:
                # Stay in B2 - generate follow-up
                followup_style = gating_result.get("followup_style", "澄清自動想法")
                b2_followup_json = await agent.run_b2_followup(
                    context=context,
                    journal_text=session.journal_text,
                    previous_b2=last_assistant_msg or "",
                    user_reply=req.user_message,
                    followup_style=followup_style
                )
                if has_unsafe_flags(b2_followup_json):
                    b2_followup_json = fallback_b2_followup()

                new_assistant_msg = render_b2_followup_text(b2_followup_json)
                # Stay in round 2

                conversation_history.append({
                    "role": "assistant",
                    "content": new_assistant_msg,
                    "mode": "B2"
                })

        else:
            # Round 3 or beyond - just complete
            session.status = "completed"
            new_assistant_msg = "本轮整理已完成。感谢你的分享，如果你想继续聊其他话题，请告诉我。"
            new_round_index = 3

    except Exception as e:
        # Fallback behavior on error
        print(f"Error in chat continue: {e}")
        if session.round_index == 1:
            b1_followup_json = fallback_b1_followup()
            new_assistant_msg = render_b1_followup_text(b1_followup_json)
        elif session.round_index == 2:
            b2_followup_json = fallback_b2_followup()
            new_assistant_msg = render_b2_followup_text(b2_followup_json)
        else:
            session.status = "completed"
            new_assistant_msg = "本轮整理已完成。"

    # Update session
    session.round_index = new_round_index
    session.conversation_history = json.dumps(conversation_history)
    session.last_assistant_mode = f"B{new_round_index}"
    session.updated_at = models.datetime.utcnow()

    db.commit()
    db.refresh(session)

    return schemas.ChatContinueResponse(
        assistant_message=new_assistant_msg,
        round_index=new_round_index,
        status=session.status,
        gating_decision=gating_decision
    )


@router.post("/chat/continue/schema")
async def get_continue_schema():
    """Return the schema for chat/continue response"""
    return {
        "session_id": "string - the therapy session ID",
        "user_message": "string - the user's message"
    }
