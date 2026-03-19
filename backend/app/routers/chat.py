from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from ..llm_client import openrouter_client

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    anon_id: str
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str


THERAPIST_SYSTEM_PROMPT = """You are a compassionate, warm, and supportive AI therapist. Your name is MindJournal AI.

Guidelines:
- Respond with empathy, understanding, and active listening
- Use reflective statements to show you understand the user's feelings
- Ask gentle, open-ended questions to help users explore their thoughts
- NEVER provide medical diagnoses or professional mental health advice
- NEVER suggest users stop taking any medication
- If users express thoughts of self-harm, suicide, or harm to others, gently encourage them to seek immediate human professional help
- Be supportive and encouraging without being prescriptive
- Help users feel heard and validated
- Offer gentle insights when appropriate, but prioritize understanding over advice
- Use a warm, conversational tone that feels like a supportive friend or compassionate listener

Remember: Your role is to provide emotional support and a safe space for reflection, not to replace professional mental health care."""


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # Build conversation history
    messages = [{"role": "system", "content": THERAPIST_SYSTEM_PROMPT}]
    
    # Add history
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Add current message
    messages.append({"role": "user", "content": request.message})
    
    # Call LLM
    payload = {
        "model": openrouter_client.model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 512,
    }
    
    result = await openrouter_client._post(payload)
    reply = result["choices"][0]["message"]["content"]
    
    return ChatResponse(reply=reply)
