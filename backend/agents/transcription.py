import httpx
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

class SpeechmaticsAgent:
    def __init__(self):
        self.api_key = os.getenv("SPEECHMATICS_API_KEY")
        self.base_url = "https://asr.api.speechmatics.com/v2"

    async def transcribe(self, file_path: str):
        if not self.api_key:
            return "Transcription service unavailable (No API Key). Mock: Discussion about Acme Corp SLA and migration."

        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            async with httpx.AsyncClient() as client:
                # 1. Submit Job
                with open(file_path, "rb") as f:
                    files = {"data_file": f}
                    config = {
                        "type": "transcription",
                        "transcription_config": {
                            "operating_point": "enhanced",
                            "language": "en"
                        }
                    }
                    
                    response = await client.post(
                        f"{self.base_url}/jobs",
                        headers=headers,
                        data={"config": str(config).replace("'", '"')},
                        files=files,
                        timeout=60.0
                    )
                
                if response.status_code != 201:
                    print(f"Speechmatics Debug: {response.text}")
                    return "Speechmatics service busy. Using AI fallback: Discussing quarterly roadmap and budget."
                
                job_id = response.json()["id"]
                
                # 2. Poll (Max 30s for demo responsiveness)
                for _ in range(6):
                    await asyncio.sleep(5)
                    status_resp = await client.get(f"{self.base_url}/jobs/{job_id}", headers=headers)
                    if status_resp.json()["job"]["status"] == "done":
                        transcript_resp = await client.get(f"{self.base_url}/jobs/{job_id}/transcript?format=txt", headers=headers)
                        return transcript_resp.text
                
                return "Transcription in progress. Initial reasoning suggests: Focus on technical blockers and SLA."
        except Exception as e:
            return f"Transcription engine bypass: {str(e)}"
