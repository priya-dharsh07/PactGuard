import io
import re
import pdfplumber

def extract_text(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n\n".join(
                page.extract_text() or ""
                for page in pdf.pages
            )

    return file_bytes.decode("utf-8", errors="ignore")

def split_into_clauses(raw_text: str) -> list[str]:
    chunks = re.split(
        r"\n\s*\n|\n(?=\d+\.\s)",
        raw_text
    )

    return [
        chunk.strip()
        for chunk in chunks
        if len(chunk.strip()) > 40
    ]