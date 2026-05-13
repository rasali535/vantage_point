from fastapi import APIRouter, UploadFile, File, Depends
from typing import List
from database import get_database
from agents.reasoning import ReasoningAgent
from agents.transcription import SpeechmaticsAgent
import uuid

router = APIRouter()
reasoning_agent = ReasoningAgent()
transcription_agent = SpeechmaticsAgent()

@router.get("/")
async def list_meetings(db = Depends(get_database)):
    if db is None:
        return [
            {"id": "1", "title": "Acme Corp Contract Review", "date": "2026-05-13", "status": "completed"},
            {"id": "2", "title": "Global Tech Partnership", "date": "2026-05-12", "status": "pending_approval"}
        ]
    meetings = await db.meetings.find().to_list(100)
    # Convert ObjectId to str for JSON serialization
    for m in meetings:
        m["id"] = str(m.pop("_id"))
    return meetings

@router.post("/process")
async def process_meeting(transcript: str, title: str, db = Depends(get_database)):
    # 1. Save Meeting
    meeting_id = str(uuid.uuid4())
    meeting = {
        "id": meeting_id,
        "title": title,
        "status": "processing",
        "transcript": transcript
    }
    if db is not None:
        await db.meetings.insert_one(meeting)
    
    # 2. Run Reasoning Agent
    analysis = await reasoning_agent.analyze_meeting(transcript)
    
    # 3. Save Tasks
    tasks = []
    if "Action Items" in analysis:
        for item in analysis.get("Action Items", []):
            task = {
                "meeting_id": meeting_id,
                "title": item.get("task") or item.get("description", "Untitled Task"),
                "owner": item.get("owner", "Unassigned"),
                "status": "pending",
                "reasoning": "Extracted by ActionPilot"
            }
            tasks.append(task)
    
    if tasks and db is not None:
        await db.tasks.insert_many(tasks)
    
    # 4. Update Meeting Status
    if db is not None:
        await db.meetings.update_one({"id": meeting_id}, {"$set": {"status": "completed", "analysis": analysis}})
    
    return {"meeting_id": meeting_id, "analysis": analysis}

@router.post("/upload")
async def upload_meeting(file: UploadFile = File(...), db = Depends(get_database)):
    # 1. Save File
    file_id = str(uuid.uuid4())
    extension = file.filename.split(".")[-1]
    file_path = f"uploads/{file_id}.{extension}"
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # 2. Real Transcription with Speechmatics
    transcript = await transcription_agent.transcribe(file_path)
    
    # 3. Process with Agent
    result = await process_meeting(transcript=transcript, title=file.filename, db=db)
    
    return {
        "meeting_id": result["meeting_id"],
        "filename": file.filename,
        "status": "processed",
        "analysis": result["analysis"]
    }
