import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import demucs.separate
import shutil
from pathlib import Path

# demucs.separate.main(["--mp3", "--two-stems", "vocals", "-n", "mdx_extra", "track with space.mp3"])

# Get base path from environment variable or use default
base_path = os.getenv("BASE_PATH", "/demucs")
app = FastAPI(
    title="Demucs Service",
    description="Service for audio source separation using Demucs",
    version="1.0.0",
    docs_url=f"{base_path}/docs",  # Update the docs URL
    openapi_url=f"{base_path}/openapi.json"  # Update the OpenAPI URL
)

@app.get("/")
async def root():
    return {"message": "Demucs Service Running"}

@app.post("/separate")
async def separate_audio(file: UploadFile = File(...)):
    if not file.filename.endswith('.mp3'):
        raise HTTPException(status_code=400, detail="Only MP3 files are supported")

    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            temp_input = Path(temp_dir) / "input.mp3"
            with temp_input.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Process with Demucs
            demucs.separate.main([
                "--mp3",
                "--two-stems", "vocals",
                "-n", "mdx_extra",
                str(temp_input)
            ])

            # The separated files will be in separated/mdx_extra/input
            output_dir = Path(temp_dir) / "separated" / "mdx_extra" / "input"

            # Create response directory if it doesn't exist
            response_dir = Path("processed_files")
            response_dir.mkdir(exist_ok=True)

            # Generate unique filename for this separation
            output_base = f"{file.filename.rsplit('.', 1)[0]}_{os.urandom(4).hex()}"

            # Move processed files to response directory
            result_files = {}
            for stem_file in output_dir.glob("*.mp3"):
                stem_name = stem_file.stem  # vocals or no_vocals
                new_path = response_dir / f"{output_base}_{stem_name}.mp3"
                shutil.copy2(stem_file, new_path)
                result_files[stem_name] = str(new_path)
            return {
                "message": "Audio separation completed",
                "files": result_files
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")
