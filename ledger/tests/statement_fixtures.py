"""Synthetic Lloyds Current-shaped statements for interpretation tests.

The layout contract is invented for this project: a text header carrying the
statement period, opening/closing balances and totals, plus transaction rows of
``date · description · type · amount · running balance``. Column padding and the
interleaved short accessibility labels mirror the observed source behaviour.
Amounts, dates and descriptions are fabricated; expected values are recorded
independently in the tests.
"""

import io

import pypdf

PAGE_WIDTH = 900
PAGE_HEIGHT = 842
LEADING = 12


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_stream(lines: list[str]) -> bytes:
    body = [f"BT /F1 9 Tf 20 {PAGE_HEIGHT - 40} Td {LEADING} TL"]
    for index, line in enumerate(lines):
        if index:
            body.append("T*")
        body.append(f"({_escape(line)}) Tj")
    body.append("ET")
    return "\n".join(body).encode("latin-1")


def statement_pdf(pages: list[list[str]]) -> bytes:
    """Render each page's lines as one text block, one line per row."""
    page_count = len(pages)
    font_number = 3 + 2 * page_count
    kids = " ".join(f"{3 + 2 * index} 0 R" for index in range(page_count))
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode(),
    ]
    for index, lines in enumerate(pages):
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
            + str(PAGE_WIDTH).encode()
            + b" "
            + str(PAGE_HEIGHT).encode()
            + b"] /Resources << /Font << /F1 "
            + str(font_number).encode()
            + b" 0 R >> >> /Contents "
            + str(4 + 2 * index).encode()
            + b" 0 R >>"
        )
        stream = _page_stream(lines)
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

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


def _transaction_block(
    day: str,
    description: str,
    transaction_type: str,
    money_in: str | None,
    money_out: str | None,
    balance: str,
) -> list[str]:
    """One observed-shaped transaction block: a label followed by its value."""
    return [
        "Date",
        f"{day}.",
        "Description",
        f"{description}.",
        "Type",
        f"{transaction_type}.",
        "Money In (£)",
        f"{money_in}." if money_in else "blank.",
        "Money Out (£)",
        f"{money_out}." if money_out else "blank.",
        "Balance (£)",
        f"{balance}.",
    ]


def lloyds_current_pages() -> list[list[str]]:
    """Two-page statement whose transaction blocks continue behind a repeated header."""
    header = [
        "logo, Lloyds Bank.",
        "Current Account statement",
        "Your Account",
        "Sort Code 12-34-56",
        "Account Number 12345678",
        "CURRENT.",
        "01 August 2026 to 31 August 2026.",
    ]
    summary = [
        "Money In.",
        "2,512.44.",
        "Balance on 01 August 2026.",
        "1,200.00.",
        "Money Out.",
        "1,065.64.",
        "Balance on 31 August 2026.",
        "2,646.80.",
    ]
    table_header = [
        "Your Transactions",
        "Column",
        "Date.",
        "Column",
        "Description.",
        "Column",
        "Type.",
        "Column",
        "Money In (£).",
        "Column",
        "Money Out (£).",
        "Column",
        "Balance (£).",
    ]
    return [
        header
        + summary
        + table_header
        + [
            "Page 1 of 2",
            *_transaction_block("01 Aug 26", "COFFEE SHOP", "Card payment", None, "3.20", "1,196.80"),
            *_transaction_block("02 Aug 26", "SALARY ACME LTD", "Bank credit", "2,500.00", None, "3,696.80"),
            *_transaction_block("03 Aug 26", "RENT PAYMENT", "DD", None, "950.00", "2,746.80"),
            *_transaction_block("04 Aug 26", "CORNER STORE", "Card payment", None, "12.44", "2,734.36"),
        ],
        [
            "Page 2 of 2",
            *table_header,
            *_transaction_block("05 Aug 26", "REFUND CORNER STORE", "Refund", "12.44", None, "2,746.80"),
            *_transaction_block("06 Aug 26", "CASH WITHDRAWAL", "Cash withdrawal", None, "100.00", "2,646.80"),
        ],
    ]


def lloyds_current_text() -> str:
    """Pages are separated by form feeds so row page numbers stay recoverable."""
    return "\f".join("\n".join(page) for page in lloyds_current_pages())


def lloyds_current_pdf() -> bytes:
    return statement_pdf(lloyds_current_pages())


def extract_text(data: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(data))
    return "\f".join(page.extract_text() for page in reader.pages)
