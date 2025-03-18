import os
from fastapi import FastAPI
import demucs.separate

# demucs.separate.main(["--mp3", "--two-stems", "vocals", "-n", "mdx_extra", "track with space.mp3"])

# Get base path from environment variable or use default
base_path = os.getenv("BASE_PATH", "/demucs")

app = FastAPI(
    title="Demucs Service",
    description="Service for audio source separation using Demucs",
    version="1.0.0",
    root_path=base_path  # Set the root path for all routes
)

@app.get("/")
async def root():
    return {"message": "Demucs Service Running"}

@app.post("/separate")
async def separate_audio():
    return {"status": "processing"}
