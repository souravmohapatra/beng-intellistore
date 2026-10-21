"""Synthetic statement-shaped files for intake tests.

These builders create deterministic bytes; expected digests are recorded as
literal constants in the tests after being computed with `shasum -a 256` outside
the application.
"""

import io

import pypdf


def text_pdf(pages: int = 1, text: str = "hello statement") -> bytes:
    """A minimal valid PDF whose pages contain selectable text."""
    font_number = 3 + 2 * pages
    kids = " ".join(f"{3 + 2 * index} 0 R" for index in range(pages))
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode(),
    ]
    for _index in range(pages):
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Resources << /Font << /F1 "
            + str(font_number).encode()
            + b" 0 R >> >> /Contents "
            + str(4 + 2 * _index).encode()
            + b" 0 R >>"
        )
        stream = f"BT /F1 12 Tf 20 250 Td ({text}) Tj ET".encode()
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode()
    return bytes(out)


def blank_pdf(pages: int = 1) -> bytes:
    """A valid PDF without selectable text (as a scanned page would be)."""
    writer = pypdf.PdfWriter()
    for _index in range(pages):
        writer.add_blank_page(width=300, height=300)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def encrypted_pdf() -> bytes:
    """A valid PDF that requires a password to open."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt("not-shared")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


CORRUPT_PDF = b"%PDF-1.7\nthis is not really a pdf\n"
BINARY_JUNK = b"\x00\x01\x02\x03\xff\xfe not text\n"
CSV_TEXT = "Date,Description,Amount\n2026-08-01,Coffee,-3.20\n".encode()
