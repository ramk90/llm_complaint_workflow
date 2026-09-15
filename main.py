import argparse
import logging
import sys
import time
from pathlib import Path

from src.config import DATA_DIR, DEFAULT_MODEL, MAX_WORKERS, OUTPUT_DIR
from src.orchestrator import process_batch, process_single_file


def setup_logging(verbose: bool = False):
    """Configure logging format and log level."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="AI-Powered Customer Complaint & Case Processing System (Gemini 3.6 Flash)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(DATA_DIR),
        help=f"Directory containing input complaint files (.pdf, .docx, .txt). Default: {DATA_DIR}",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(OUTPUT_DIR),
        help=f"Directory to save generated artifacts. Default: {OUTPUT_DIR}",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to a single complaint file to process (overrides batch data-dir mode).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"Maximum thread pool worker count for batch mode. Default: {MAX_WORKERS}",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Gemini model name to use. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed DEBUG logging.",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger("main")
    logger.info("Starting AI Customer Complaint Workflow System...")
    start_time = time.time()

    out_path = Path(args.output_dir)

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f"Specified file does not exist: {file_path}")
            sys.exit(1)
        logger.info(f"Running single-file mode on: {file_path}")
        result = process_single_file(file_path=file_path, model_name=args.model, output_dir=out_path)
        
        print("\n" + "=" * 60)
        print(f"FILE: {result.filename}")
        print(f"STATUS: {result.status}")
        if result.status == "SUCCESS" and result.analysis:
            print(f"CASE ID: {result.analysis.case_id}")
            print(f"CUSTOMER: {result.analysis.customer.name or 'N/A'}")
            print(f"CATEGORY: {result.analysis.category.value}")
            print(f"URGENCY: {result.analysis.urgency.value}")
            print(f"SENTIMENT: {result.analysis.sentiment.value}")
            print(f"SUMMARY: {result.analysis.summary}")
        else:
            print(f"ERROR: {result.error_message}")
        print("=" * 60)

    else:
        in_path = Path(args.data_dir)
        if not in_path.exists():
            logger.error(f"Input directory does not exist: {in_path}")
            sys.exit(1)

        logger.info(f"Running batch mode on directory: {in_path}")
        results = process_batch(
            data_dir=in_path,
            output_dir=out_path,
            max_workers=args.workers,
            model_name=args.model,
        )

        success_count = sum(1 for r in results if r.status == "SUCCESS")
        fail_count = len(results) - success_count
        elapsed = round(time.time() - start_time, 2)

        print("\n" + "=" * 60)
        print("BATCH PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total Files Processed : {len(results)}")
        print(f"Successful Workflows  : {success_count}")
        print(f"Failed Workflows      : {fail_count}")
        print(f"Total Execution Time  : {elapsed} seconds")
        print(f"Consolidated CSV      : {out_path / 'final_report.csv'}")
        print(f"Structured JSON Output: {out_path / 'structured_data'}")
        print(f"Customer Email Output : {out_path / 'customer_emails'}")
        print(f"Executive Summaries   : {out_path / 'case_summaries'}")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
