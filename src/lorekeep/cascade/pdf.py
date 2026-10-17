"""Step 3: a PDF converted to Markdown by MarkItDown (with its `pdf` extra).

MarkItDown is imported on first use: it takes a fraction of a second, which `lorekeep --help`
should not pay.
"""

from __future__ import annotations

import io
from importlib import metadata

from lorekeep.cascade.step import Converted, Fallthrough

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
        converter=f"markitdown {metadata.version('markitdown')}",
        original_ext="pdf",
        title=(result.title or "").strip() or None,
    )
