from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from datetime import datetime

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

    print(f"[CHAT/CONTINUE] >>> request received: session_id={req.session_id}, user_message='{req.user_message[:80]}'")

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

    print(f"[CHAT/CONTINUE] round={session.round_index}, history_count={len(conversation_history)}")

    try:
        if session.round_index == 1:
            # B1 stage - check if ready for B2
            print(f"[CHAT/CONTINUE] Calling gate_b1_to_b2 with user_reply='{req.user_message[:50]}'")
            gating_result = await agent.gate_b1_to_b2(
                journal_text=session.journal_text,
                assistant_b1=last_assistant_msg or "",
                user_reply=req.user_message
            )
            print(f"[CHAT/CONTINUE] gate_b1_to_b2 result: {gating_result.get('decision')}")

            gating_decision = schemas.GatingDecision(
                decision=gating_result.get("decision", "STAY_IN_B1"),
                reason=gating_result.get("reason", ""),
                evidence=gating_result.get("evidence", []),
                followup_style=gating_result.get("followup_style", "情緒承接")
            )

            if gating_result.get("decision") == "READY_FOR_B2":
                print("[CHAT/CONTINUE] Decision: READY_FOR_B2, generating B2")
                conv_str = format_conversation_for_llm(conversation_history)
                b2_json = await agent.run_b2(context, conv_str, req.user_message)
                print(f"[CHAT/CONTINUE] B2 generated, unsafe_flags={has_unsafe_flags(b2_json)}")
                if has_unsafe_flags(b2_json):
                    print("[CHAT/CONTINUE] B2 unsafe flags triggered, using fallback")
                    b2_json = fallback_b2()

                new_assistant_msg = render_b2_text(b2_json)
                new_round_index = 2

                conversation_history.append({
                    "role": "assistant",
                    "content": new_assistant_msg,
                    "mode": "B2"
                })
            else:
                print("[CHAT/CONTINUE] Decision: STAY_IN_B1, generating B1 followup")
                followup_style = gating_result.get("followup_style", "情緒承接")
                b1_followup_json = await agent.run_b1_followup(
                    context=context,
                    journal_text=session.journal_text,
                    previous_b1=last_assistant_msg or "",
                    user_reply=req.user_message,
                    followup_style=followup_style
                )
                print(f"[CHAT/CONTINUE] B1 followup generated, unsafe_flags={has_unsafe_flags(b1_followup_json)}")
                if has_unsafe_flags(b1_followup_json):
                    print("[CHAT/CONTINUE] B1 followup unsafe flags triggered, using fallback")
                    b1_followup_json = fallback_b1_followup()

                new_assistant_msg = render_b1_followup_text(b1_followup_json)

                conversation_history.append({
                    "role": "assistant",
                    "content": new_assistant_msg,
                    "mode": "B1"
                })

        elif session.round_index == 2:
            # B2 stage - check if ready for B3
            print(f"[CHAT/CONTINUE] Calling gate_b2_to_b3 with user_reply='{req.user_message[:50]}'")
            gating_result = await agent.gate_b2_to_b3(
                journal_text=session.journal_text,
                assistant_b2=last_assistant_msg or "",
                user_reply=req.user_message
            )
            print(f"[CHAT/CONTINUE] gate_b2_to_b3 result: {gating_result.get('decision')}")

            gating_decision = schemas.GatingDecision(
                decision=gating_result.get("decision", "STAY_IN_B2"),
                reason=gating_result.get("reason", ""),
                evidence=gating_result.get("evidence", []),
                followup_style=gating_result.get("followup_style", "澄清自動想法")
            )

            if gating_result.get("decision") == "READY_FOR_B3":
                print("[CHAT/CONTINUE] Decision: READY_FOR_B3, generating B3")
                conv_str = format_conversation_for_llm(conversation_history)
                b3_json = await agent.run_b3(context, conv_str, req.user_message)
                print(f"[CHAT/CONTINUE] B3 generated, unsafe_flags={has_unsafe_flags(b3_json)}")
                if has_unsafe_flags(b3_json):
                    print("[CHAT/CONTINUE] B3 unsafe flags triggered, using fallback")
                    b3_json = fallback_b3()

                new_assistant_msg = render_b3_text(b3_json)
                new_round_index = 3

                conversation_history.append({
                    "role": "assistant",
                    "content": new_assistant_msg,
                    "mode": "B3"
                })

                session.status = "completed"
            else:
                print("[CHAT/CONTINUE] Decision: STAY_IN_B2, generating B2 followup")
                followup_style = gating_result.get("followup_style", "澄清自動想法")
                b2_followup_json = await agent.run_b2_followup(
                    context=context,
                    journal_text=session.journal_text,
                    previous_b2=last_assistant_msg or "",
                    user_reply=req.user_message,
                    followup_style=followup_style
                )
                print(f"[CHAT/CONTINUE] B2 followup generated, unsafe_flags={has_unsafe_flags(b2_followup_json)}")
                if has_unsafe_flags(b2_followup_json):
                    print("[CHAT/CONTINUE] B2 followup unsafe flags triggered, using fallback")
                    b2_followup_json = fallback_b2_followup()

                new_assistant_msg = render_b2_followup_text(b2_followup_json)

                conversation_history.append({
                    "role": "assistant",
                    "content": new_assistant_msg,
                    "mode": "B2"
                })

        else:
            # Round 3 or beyond - just complete
            print("[CHAT/CONTINUE] Round >= 3, marking session completed")
            session.status = "completed"
            new_assistant_msg = "本轮整理已完成。如果你有其他想聊的，随时告诉我。"
            new_round_index = 3

    except Exception as e:
        print(f"[CHAT/CONTINUE] ERROR: {e}")
        if session.round_index == 1:
            b1_followup_json = fallback_b1_followup()
            new_assistant_msg = render_b1_followup_text(b1_followup_json)
        elif session.round_index == 2:
            b2_followup_json = fallback_b2_followup()
            new_assistant_msg = render_b2_followup_text(b2_followup_json)
        else:
            session.status = "completed"
            new_assistant_msg = "出现了一点问题，请稍后重试。"

    # Update session
    session.round_index = new_round_index
    session.conversation_history = json.dumps(conversation_history)
    session.last_assistant_mode = f"B{new_round_index}"
    session.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(session)

    print(f"[CHAT/CONTINUE] <<< returning: round={new_round_index}, status={session.status}, msg_len={len(new_assistant_msg)}")

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
