#!/usr/bin/env python3
"""
Simple PDF OCR script that processes PDFs from /input folder
and saves results to /output/timestamp/ directory.
No system dependencies required - everything in Python!
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

import easyocr
import pdfplumber
from PIL import Image
import io
import numpy as np

# Initialize OCR reader (downloads model on first run)
reader = easyocr.Reader(['en'], gpu=False)


def setup_folders():
    """Create input/output folder structure."""
    input_dir = Path("input")
    output_dir = Path("output")
    
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    return input_dir, output_dir


def get_timestamp_folder(output_dir: Path) -> tuple[Path, Path]:
    """Create and return timestamped output folders."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_dir = output_dir / timestamp
    original_dir = timestamp_dir / "original"
    processed_dir = timestamp_dir / "processed"
    
    original_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    return original_dir, processed_dir


def setup_logging(timestamp_dir: Path) -> logging.Logger:
    """Configure logging to file in timestamp directory."""
    log_file = timestamp_dir / "ocr_log.txt"
    
    logger = logging.getLogger("pdf_ocr")
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def check_dependencies(logger: logging.Logger) -> bool:
    """Verify EasyOCR is available."""
    try:
        import easyocr
        logger.info("✓ EasyOCR available (pure Python - no system dependencies needed)")
        return True
    except ImportError:
        logger.error("❌ EasyOCR not found. Install with: uv sync")
        return False


def extract_text_from_pdf(pdf_path: Path, logger: logging.Logger) -> str:
    """Extract text from PDF using OCR."""
    try:
        full_text = ""
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Try to extract text directly first
                text = page.extract_text()
                if text and text.strip():
                    full_text += f"\n--- Page {page_num} ---\n{text}"
                    continue
                
                # If no text, use OCR on the rendered image
                try:
                    # Render page to PIL Image
                    pil_image = page.to_image(resolution=150).original
                    # Convert PIL Image to numpy array
                    img_array = np.array(pil_image)
                    
                    # Perform OCR
                    results = reader.readtext(img_array, detail=0)
                    if results:
                        ocr_text = "\n".join(results)
                        full_text += f"\n--- Page {page_num} (OCR) ---\n{ocr_text}"
                    else:
                        logger.warning(f"No text found on page {page_num}")
                except Exception as e:
                    logger.warning(f"Could not OCR page {page_num}: {e}")
        
        return full_text.strip()
    except Exception as e:
        logger.error(f"Error processing {pdf_path.name}: {e}")
        return ""


def process_pdfs(input_dir: Path, original_dir: Path, processed_dir: Path, logger: logging.Logger) -> int:
    """Process all PDFs in input folder."""
    pdf_files = list(input_dir.glob("*.pdf"))
    
    logger.info(f"Found {len(pdf_files)} PDF file(s). Starting OCR...")
    
    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        
        # Extract text
        text = extract_text_from_pdf(pdf_path, logger)
        
        # Save extracted text
        output_file = processed_dir / f"{pdf_path.stem}.txt"
        output_file.write_text(text, encoding="utf-8")
        
        # Move original PDF
        shutil.move(str(pdf_path), str(original_dir / pdf_path.name))
        
        logger.info(f"  ✓ Saved: {output_file.name}")
    
    return len(pdf_files)


def main():
    """Main entry point."""
    input_dir, output_dir = setup_folders()
    
    # Check for PDFs first before creating timestamp folder
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in /input folder.")
        return
    
    original_dir, processed_dir = get_timestamp_folder(output_dir)
    timestamp_dir = original_dir.parent
    
    logger = setup_logging(timestamp_dir)
    
    logger.info("PDF OCR - Processing PDFs from /input folder")
    logger.info(f"Input folder:  {input_dir.resolve()}")
    logger.info(f"Output folder: {timestamp_dir.resolve()}")
    
    # Check dependencies
    if not check_dependencies(logger):
        logger.info("\n⚠️  Process aborted due to missing dependencies.")
        return
    
    count = process_pdfs(input_dir, original_dir, processed_dir, logger)
    
    logger.info(f"✓ Completed! {count} PDF(s) processed.")
    logger.info(f"Results saved to: {timestamp_dir.name}/")


if __name__ == "__main__":
    main()
