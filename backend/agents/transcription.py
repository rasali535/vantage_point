import asyncio
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


class SpeechmaticsAgent:
    """Speechmatics transcription adapter; never fabricates transcript text."""

    def __init__(self):
        self.api_key = os.getenv("SPEECHMATICS_API_KEY")
        self.base_url = "https://asr.api.speechmatics.com/v2"

    async def transcribe(self, file_path: str) -> str:
        if not self.api_key:
            raise RuntimeError("Speechmatics is not configured.")
        if not file_path or not os.path.isfile(file_path):
            raise RuntimeError("Audio file is unavailable.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        config = {
            "type": "transcription",
            "transcription_config": {
                "operating_point": "enhanced",
                "language": "en",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
                with open(file_path, "rb") as audio_file:
                    response = await client.post(
                        f"{self.base_url}/jobs",
                        headers=headers,
                        data={"config": json.dumps(config)},
                        files={"data_file": audio_file},
                    )
                response.raise_for_status()
                job_id = response.json().get("id")
                if not job_id:
                    raise RuntimeError("Speechmatics did not return a job ID.")

                for _ in range(3):
                    await asyncio.sleep(1)
                    status_response = await client.get(
                        f"{self.base_url}/jobs/{job_id}",
                        headers=headers,
                    )
                    status_response.raise_for_status()
                    job_status = status_response.json().get("job", {}).get("status")
                    if job_status == "done":
                        transcript_response = await client.get(
                            f"{self.base_url}/jobs/{job_id}/transcript?format=txt",
                            headers=headers,
                        )
                        transcript_response.raise_for_status()
                        transcript = transcript_response.text.strip()
                        if transcript:
                            return transcript
                        raise RuntimeError("Speechmatics returned an empty transcript.")
                    if job_status in {"rejected", "deleted"}:
                        raise RuntimeError("Speechmatics could not process the audio.")

        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise RuntimeError("Speechmatics transcription request failed.") from exc

        raise RuntimeError("Speechmatics transcription is still processing. Please retry.")
