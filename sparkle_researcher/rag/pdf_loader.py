from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)


@dataclass
class PdfPage:
    page_number: int
    text: str


def extract_pdf_pages(path: Path) -> list[PdfPage]:
    reader = PdfReader(str(path))
    pages: list[PdfPage] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = normalize_text(text)
        if text:
            pages.append(PdfPage(page_number=index, text=text))
    return pages


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\x00", " ").split())
