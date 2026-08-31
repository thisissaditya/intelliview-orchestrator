from fastapi import FastAPI
from processing import run_video_analysis
from pydantic import BaseModel

app = FastAPI(
    title="CV Processing Service",
    description="Standalone OpenCV + MediaPipe microservice",
    version="1.0.0",
)


class VideoRequest(BaseModel):
    session_id: str


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "cv-processing",
    }


@app.post("/analyze-video")
async def analyze_video(request: VideoRequest):
    """
    Run OpenCV + MediaPipe video analysis.
    """
    return run_video_analysis(request.session_id)
