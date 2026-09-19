import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel

from src.config import DATA_DIR, DEFAULT_MODEL, MAX_WORKERS, OUTPUT_DIR
from src.orchestrator import process_batch, process_single_file
from src.schemas import WorkflowResult

app = FastAPI(
    title="AI Customer Complaint & Case Processing API",
    description="FastAPI service for automated document processing, entity extraction, email drafting, and case summaries powered by Google Gemini 2.5 Flash.",
    version="1.0.0",
)


class TriggerRequest(BaseModel):
    data_dir: Optional[str] = str(DATA_DIR)
    output_dir: Optional[str] = str(OUTPUT_DIR)
    workers: Optional[int] = MAX_WORKERS
    model: Optional[str] = DEFAULT_MODEL


@app.get("/")
def read_root():
    return {
        "service": "AI Customer Complaint & Case Processing API",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "trigger_batch": "POST /trigger",
            "process_file_upload": "POST /process-file",
        },
    }


@app.get("/health")
def health_check():
    """Service health check endpoint."""
    return {"status": "ok", "service": "complaint-workflow-api"}


@app.post("/trigger")
def trigger_batch_processing(request: TriggerRequest):
    """
    Trigger batch processing of all documents in the specified data directory.
    Returns summary statistics and workflow execution status.
    """
    in_dir = Path(request.data_dir)
    out_dir = Path(request.output_dir)

    if not in_dir.exists():
        raise HTTPException(status_code=404, detail=f"Data directory '{in_dir}' does not exist.")

    results = process_batch(
        data_dir=in_dir,
        output_dir=out_dir,
        max_workers=request.workers,
        model_name=request.model,
    )

    success_count = sum(1 for r in results if r.status == "SUCCESS")

    return {
        "status": "completed",
        "total_files": len(results),
        "successful": success_count,
        "failed": len(results) - success_count,
        "csv_report": str((out_dir / "final_report.csv").resolve()),
        "results": results,
    }


@app.post("/process-file", response_model=WorkflowResult)
async def process_file_upload(file: UploadFile = File(...), model: Optional[str] = DEFAULT_MODEL):
    """
    Upload a single complaint file (.txt, .pdf, .docx) for immediate execution.
    Returns the complete structured analysis, customer response email, and executive summary.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".txt", ".pdf", ".docx"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{suffix}'. Supported: .txt, .pdf, .docx",
        )

    # Save uploaded file to a temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file_path = Path(tmp_dir) / file.filename
        with open(tmp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = process_single_file(file_path=tmp_file_path, model_name=model)
        return result
