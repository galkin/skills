"""Step 3: a PDF converted to Markdown by MarkItDown (with its `pdf` extra).

MarkItDown is imported on first use: it takes a fraction of a second, which `lorekeep --help`
should not pay. The title is read with pdfminer.six, the parser MarkItDown's `pdf` extra brings.
"""

from __future__ import annotations

import io
from importlib import metadata

from lorekeep.cascade.step import Converted, Fallthrough

NAME = "markitdown"
"""The first word of the `converter` this step writes: `markitdown <version>`."""

_MAGIC = b"%PDF-"


def convert_pdf(received: bytes, url: str, charset: str | None) -> Converted | Fallthrough:
    """The PDF's text as Markdown; bytes that are not a PDF are refused, never guessed at.

    MarkItDown falls back to its HTML or plain-text converter when a stream labelled PDF is not
    one, so the bytes are checked first.
    """
    from markitdown import MarkItDown, MarkItDownException, StreamInfo

    if not received.lstrip().startswith(_MAGIC):
        return Fallthrough("served as application/pdf but the bytes are not a PDF")
    try:
        result = MarkItDown(enable_plugins=False).convert_stream(
            io.BytesIO(received),
            stream_info=StreamInfo(mimetype="application/pdf", extension=".pdf"),
        )
    except MarkItDownException as error:
        return Fallthrough(f"the PDF could not be converted ({type(error).__name__})")
    markdown = result.markdown.strip()
    if not markdown:
        return Fallthrough("no content: the PDF yields no text")
    return Converted(
        markdown=(markdown + "\n").encode("utf-8"),
        converter=f"{NAME} {metadata.version(NAME)}",
        original_ext="pdf",
        title=metadata_title(received) or (result.title or "").strip() or first_line(markdown),
    )


def metadata_title(received: bytes) -> str | None:
    """The `Title` of the PDF's document information dictionary, when it names one."""
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdftypes import resolve1
    from pdfminer.psexceptions import PSException
    from pdfminer.utils import decode_text

    try:
        document = PDFDocument(PDFParser(io.BytesIO(received)))
        found = [resolve1(info.get("Title")) for info in document.info]
    except (PSException, KeyError, TypeError, ValueError):  # an unreadable Info: no title
        return None
    for value in found:
        text = decode_text(value) if isinstance(value, bytes) else value
        if isinstance(text, str) and (title := " ".join(text.split())):
            return title
    return None


def first_line(markdown: str) -> str | None:
    """The first non-empty line of the PDF's text, its whitespace squeezed."""
    return next((" ".join(line.split()) for line in markdown.splitlines() if line.strip()), None)
