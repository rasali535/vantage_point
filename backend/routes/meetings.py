import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
from database import get_database
from agents.reasoning import boardroom
from agents.transcription import SpeechmaticsAgent
import uuid

router = APIRouter()

# Lazy load transcription agent
_transcription_agent = None

def get_transcription_agent():
    global _transcription_agent
    if _transcription_agent is None:
        _transcription_agent = SpeechmaticsAgent()
    return _transcription_agent

@router.get("/")
async def list_meetings(db = Depends(get_database)):
    if db is None:
        return [
            {"id": "1", "title": "Inbound Invoice: AWS-99283", "date": "2026-05-13", "status": "completed", "type": "invoice", "yield_bps": 2.4, "strategy": "Sell TSLAx"},
            {"id": "2", "title": "Weekly Payroll Disbursement", "date": "2026-05-12", "status": "pending_approval", "type": "payroll", "yield_bps": 0.0, "strategy": "Delay ACH"},
            {"id": "3", "title": "Tax-Loss Harvesting: Q2 Batch", "date": "2026-05-11", "status": "completed", "type": "tax", "yield_bps": 12.8, "strategy": "Swap BTCx"},
            {"id": "4", "title": "Tokenized Bond Yield Capture", "date": "2026-05-10", "status": "completed", "type": "bond", "yield_bps": 4.5, "strategy": "Compound Ondo"}
        ]
    meetings = await db.meetings.find().to_list(100)
    for m in meetings:
        m["id"] = str(m.pop("_id"))
    return meetings

@router.post("/process")
async def process_meeting(transcript: str, title: str, image_path: str = None, db = Depends(get_database)):
    # 1. Save Meeting
    meeting_id = str(uuid.uuid4())
    meeting = {
        "id": meeting_id,
        "title": title,
        "status": "processing",
        "transcript": transcript,
        "image_path": image_path
    }
    if db is not None:
        await db.meetings.insert_one(meeting)
    
    # 2. Run Boardroom Deliberation (Multi-Agent Consensus)
    # For meetings, we treat it as a general consensus task
    analysis = await boardroom.deliberate(
        ticker={"last": 0, "change_percent": 0},
        ohlc=[],
        pair="Meeting Analysis"
    )
    
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
async def upload_meeting(file: UploadFile = File(...), context_image: UploadFile = File(None), db = Depends(get_database)):
    file_id = str(uuid.uuid4())
    extension = file.filename.split(".")[-1]
    
    # Use /tmp for serverless environments (Vercel)
    upload_dir = "/tmp" if os.environ.get("VERCEL") else "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file_path = os.path.join(upload_dir, f"{file_id}.{extension}")
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # 2. Save Context Image (Optional)
    image_path = None
    if context_image:
        img_id = str(uuid.uuid4())
        img_ext = context_image.filename.split(".")[-1]
        image_path = os.path.join(upload_dir, f"{img_id}.{img_ext}")
        with open(image_path, "wb") as buffer:
            img_content = await context_image.read()
            buffer.write(img_content)
    
    try:
        # 3. Real Transcription with Speechmatics
        t_agent = get_transcription_agent()
        transcript = await t_agent.transcribe(file_path)
        
        # 4. Process with Agent (Gemini Multimodal)
        result = await process_meeting(transcript=transcript, title=file.filename, image_path=image_path, db=db)
        
        return {
            "meeting_id": result["meeting_id"],
            "filename": file.filename,
            "status": "processed",
            "analysis": result["analysis"]
        }
    except Exception as e:
        print(f"ERROR in upload_meeting: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
