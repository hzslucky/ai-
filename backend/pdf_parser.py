"""PDF resume parsing and text cleaning."""

import re
from io import BytesIO

import pdfplumber


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract raw text from a PDF file (supports multi-page)."""
    full_text = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
    return "\n".join(full_text)


def clean_text(raw_text: str) -> str:
    """Clean and normalize extracted text."""
    # Remove excessive whitespace
    text = re.sub(r"[ \t]+", " ", raw_text)
    # Collapse 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove non-printable characters except common punctuation and newlines
    text = re.sub(r"[^\x20-\x7E一-鿿　-〿＀-￯\n]", "", text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]
    # Remove empty consecutive duplicate lines
    cleaned = []
    for line in lines:
        if line or (cleaned and cleaned[-1] != ""):
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def parse_resume(file_bytes: bytes) -> str:
    """Full pipeline: extract and clean PDF resume text."""
    raw = extract_text_from_pdf(file_bytes)
    return clean_text(raw)
