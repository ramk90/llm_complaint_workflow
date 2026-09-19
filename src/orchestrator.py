import csv
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Union

from src.chains import (
    extract_complaint_data,
    generate_customer_email,
    generate_executive_summary,
)
from src.config import (
    CASE_SUMMARIES_DIR,
    CUSTOMER_EMAILS_DIR,
    DATA_DIR,
    DEFAULT_MODEL,
    FINAL_REPORT_PATH,
    MAX_WORKERS,
    OUTPUT_DIR,
    STRUCTURED_DATA_DIR,
    ensure_directories,
)
from src.ingest import extract_text_from_file
from src.schemas import WorkflowResult

logger = logging.getLogger(__name__)


def process_single_file(
    file_path: Union[str, Path],
    model_name: str = DEFAULT_MODEL,
    output_dir: Optional[Path] = None,
) -> WorkflowResult:
    """
    Process a single complaint file through the full multi-step LLM workflow:
    1. Text Extraction
    2. Structured Complaint Analysis (Step 1)
    3. Customer Email Response Drafting (Step 2)
    4. Executive Internal Summary Generation (Step 3)
    5. Artifact Persistence (JSON, Email TXT, Summary TXT)
    """
    path = Path(file_path).resolve()
    filename = path.name
    file_stem = path.stem
    start_time = time.time()

    logger.info(f"Processing document: {filename}")

    # Set output directories
    base_out = output_dir or OUTPUT_DIR
    struct_dir = base_out / "structured_data"
    email_dir = base_out / "customer_emails"
    summary_dir = base_out / "case_summaries"

    for d in [struct_dir, email_dir, summary_dir]:
        d.mkdir(parents=True, exist_ok=True)

    try:
        # Step 0: Ingestion
        raw_text = extract_text_from_file(path)
        logger.info(f"[{filename}] Successfully extracted {len(raw_text)} characters.")

        # Step 1: Structured Extraction
        analysis = extract_complaint_data(raw_text=raw_text, filename=filename, model_name=model_name)
        logger.info(f"[{filename}] Analysis complete. Case ID: {analysis.case_id}, Urgency: {analysis.urgency}")

        # Step 2: Customer Email Generation
        email_output = generate_customer_email(analysis=analysis, model_name=model_name)
        logger.info(f"[{filename}] Email generated. Subject: '{email_output.email_subject}'")

        # Step 3: Executive Summary Generation
        summary_output = generate_executive_summary(analysis=analysis, model_name=model_name)
        logger.info(f"[{filename}] Executive summary generated.")

        # Save Structured JSON Artifact
        json_path = struct_dir / f"{file_stem}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(analysis.model_dump(), indent=2, ensure_ascii=False))

        # Save Customer Email Artifact
        email_path = email_dir / f"{file_stem}_email.txt"
        with open(email_path, "w", encoding="utf-8") as f:
            f.write(f"SUBJECT: {email_output.email_subject}\n")
            f.write(f"TONE: {email_output.tone}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"{email_output.email_body}\n\n")
            if email_output.next_steps_for_customer:
                f.write("NEXT STEPS FOR CUSTOMER:\n")
                for step in email_output.next_steps_for_customer:
                    f.write(f"- {step}\n")

        # Save Executive Summary Artifact
        summary_path = summary_dir / f"{file_stem}_summary.txt"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"HEADLINE: {summary_output.executive_headline}\n")
            f.write(f"RISK ASSESSMENT: {summary_output.risk_assessment}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"SUMMARY:\n{summary_output.brief_summary}\n\n")
            f.write(f"BUSINESS IMPACT:\n{summary_output.business_impact}\n\n")
            f.write("ACTION PLAN ROADMAP:\n")
            for action in summary_output.action_plan:
                f.write(f"- {action}\n")

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"[{filename}] Completed workflow successfully in {elapsed}s.")

        return WorkflowResult(
            filename=filename,
            file_path=str(path),
            status="SUCCESS",
            analysis=analysis,
            email=email_output,
            summary=summary_output,
            error_message=None,
            processing_time_sec=elapsed,
        )

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        err_msg = str(e)
        logger.error(f"[{filename}] Workflow failed after {elapsed}s: {err_msg}")
        return WorkflowResult(
            filename=filename,
            file_path=str(path),
            status="FAILED",
            analysis=None,
            email=None,
            summary=None,
            error_message=err_msg,
            processing_time_sec=elapsed,
        )


def process_batch(
    data_dir: Union[str, Path] = DATA_DIR,
    output_dir: Union[str, Path] = OUTPUT_DIR,
    max_workers: int = MAX_WORKERS,
    model_name: str = DEFAULT_MODEL,
) -> List[WorkflowResult]:
    """
    Process all documents in data_dir in parallel batch execution.
    Generates structured outputs, email responses, case summaries, and a consolidated CSV report.
    """
    in_path = Path(data_dir)
    out_path = Path(output_dir)
    ensure_directories(out_path)

    supported_extensions = {".txt", ".pdf", ".docx"}
    files_to_process = [
        p for p in in_path.glob("*") if p.is_file() and p.suffix.lower() in supported_extensions
    ]

    if not files_to_process:
        logger.warning(f"No valid documents (.txt, .pdf, .docx) found in {in_path.resolve()}")
        return []

    logger.info(f"Starting batch processing of {len(files_to_process)} document(s) with max_workers={max_workers}")

    results: List[WorkflowResult] = []

    # Execute in thread pool for parallel batch execution
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, file_p, model_name, out_path): file_p
            for file_p in files_to_process
        }
        for future in as_completed(future_to_file):
            res = future.result()
            results.append(res)

    # Sort results by filename for predictable report ordering
    results.sort(key=lambda r: r.filename)

    # Write Consolidated CSV Report
    csv_report_path = out_path / "final_report.csv"
    fieldnames = [
        "case_id",
        "filename",
        "file_path",
        "status",
        "customer_name",
        "customer_email",
        "category",
        "urgency",
        "sentiment",
        "financial_impact_usd",
        "assigned_department",
        "sla_hours",
        "summary",
        "error_message",
        "processing_time_sec",
    ]

    with open(csv_report_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            if r.status == "SUCCESS" and r.analysis:
                a = r.analysis
                row = {
                    "case_id": a.case_id,
                    "filename": r.filename,
                    "file_path": r.file_path,
                    "status": r.status,
                    "customer_name": a.customer.name or "",
                    "customer_email": a.customer.email or "",
                    "category": a.category.value if a.category else "",
                    "urgency": a.urgency.value if a.urgency else "",
                    "sentiment": a.sentiment.value if a.sentiment else "",
                    "financial_impact_usd": a.details.financial_impact_usd or 0.0,
                    "assigned_department": a.assigned_department or "",
                    "sla_hours": a.sla_hours or 0,
                    "summary": a.summary or "",
                    "error_message": "",
                    "processing_time_sec": r.processing_time_sec,
                }
            else:
                row = {
                    "case_id": "N/A",
                    "filename": r.filename,
                    "file_path": r.file_path,
                    "status": r.status,
                    "customer_name": "",
                    "customer_email": "",
                    "category": "",
                    "urgency": "",
                    "sentiment": "",
                    "financial_impact_usd": 0.0,
                    "assigned_department": "",
                    "sla_hours": 0,
                    "summary": "",
                    "error_message": r.error_message or "Unknown error",
                    "processing_time_sec": r.processing_time_sec,
                }
            writer.writerow(row)

    logger.info(f"Consolidated CSV report written to: {csv_report_path.resolve()}")
    return results
