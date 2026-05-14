from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

import routes.meetings
import routes.trading
import routes.chat

app = FastAPI(title="ActionPilot API")

# CORS setup for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for Vercel deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.meetings.router, prefix="/api/meetings", tags=["Meetings"])
app.include_router(routes.trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(routes.chat.router, prefix="/api/chat", tags=["Chat"])

# Mock DB Models
class Task(BaseModel):
    id: str
    meeting_id: str
    title: str
    owner: str
    status: str
    reasoning: str

class Meeting(BaseModel):
    id: str
    title: str
    date: str
    status: str

@app.get("/")
async def root():
    return {"message": "ActionPilot API is running"}

@app.get("/meetings", response_model=List[Meeting])
async def get_meetings():
    return [
        {"id": "1", "title": "Quarterly Sales Sync", "date": "2026-05-13", "status": "processed"},
        {"id": "2", "title": "Product Roadmap Review", "date": "2026-05-12", "status": "pending_approval"}
    ]


@app.get("/tasks/{meeting_id}", response_model=List[Task])
async def get_tasks(meeting_id: str):
    return [
        {"id": "t1", "meeting_id": meeting_id, "title": "Send follow-up email to stakeholders", "owner": "Alice", "status": "pending", "reasoning": "Determined from meeting summary: Alice committed to follow up by Friday."},
        {"id": "t2", "meeting_id": meeting_id, "title": "Update CRM with new deal stage", "owner": "System", "status": "completed", "reasoning": "Autonomous action: Meeting confirmed deal moved to 'Proposal' stage."}
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
