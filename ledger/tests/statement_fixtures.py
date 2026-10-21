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


def lloyds_credit_pages(statement_date: str = "07 September 2026") -> list[list[str]]:
    """Cover + one transaction page + breakdown for the Lloyds Credit contract."""
    return [
        [
            "Your credit card statement",
            statement_date,
            "Lloyds Bank Cashback",
            "Credit Card",
            "Previous balance        400.00",
            "Payments received       400.00",
            "To reach your account by 01 October 2026",
            "Your new balance",
            "860.00",
        ],
        [
            "Cardholder                      MR TEST CARDHOLDER",
            "Card Ending Date of transaction Date entered Description Amount £",
            "BALANCE FROM PREVIOUS STATEMENT               400.00",
            "7 30 JULY 30 JULY DIRECT DEBIT PAYMENT - THANK YOU      400.00CR",
            "7 03 JULY 06 JULY COFFEE HOUSE GB        21.00",
            "7 04 JULY 06 JULY SUPERMARKET LONDON GB        33.50",
            "7 04 JULY 06 JULY NON-STERLING PURCHASE FEE         0.75",
            "7 17 JULY 20 JULY CAFE STOCKHOLM SE       120.00",
            "987.65SEK @ 11.30",
            "7 21 JULY 22 JULY RESTAURANT STOCKHOLM SE        64.00",
            "7 02 AUGUST 03 AUGUST ELECTRONICS LONDON GB       620.75",
        ],
        [
            "Card Ending Date of transaction Date entered Description Amount £",
            "Breakdown of balance",
            "New balance              860.00",
        ],
    ]


def lloyds_credit_year_boundary_pages() -> list[list[str]]:
    """Statement dated January: December rows belong to the previous year."""
    return [
        [
            "Your credit card statement",
            "06 January 2027",
            "Lloyds Bank Cashback",
            "Credit Card",
            "Payments received       0.00",
            "Your new balance",
            "125.00",
        ],
        [
            "Card Ending Date of transaction Date entered Description Amount £",
            "BALANCE FROM PREVIOUS STATEMENT               90.00",
            "7 30 DECEMBER 31 DECEMBER SHOP GB        10.00",
            "7 02 JANUARY 04 JANUARY SHOP TWO GB        20.00",
            "7 30 DECEMBER 02 JANUARY SHOP THREE GB        5.00",
            "New balance              125.00",
        ],
    ]


def lloyds_credit_pdf(pages: list[list[str]] | None = None) -> bytes:
    return statement_pdf(pages or lloyds_credit_pages())


def lloyds_credit_text(pages: list[list[str]] | None = None) -> str:
    return "\f".join("\n".join(page) for page in (pages or lloyds_credit_pages()))


def positioned_statement_pdf(pages: list[list[tuple[float, float, str]]]) -> bytes:
    """Render tokens at explicit (x, y) positions, one text object each."""
    page_count = len(pages)
    font_number = 3 + 2 * page_count
    kids = " ".join(f"{3 + 2 * index} 0 R" for index in range(page_count))
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode(),
    ]
    for index, tokens in enumerate(pages):
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 "
            + str(font_number).encode()
            + b" 0 R >> >> /Contents "
            + str(4 + 2 * index).encode()
            + b" 0 R >>"
        )
        commands = ["BT /F1 9 Tf"]
        for x, y, text in tokens:
            commands.append(f"1 0 0 1 {x} {y} Tm ({_escape(text)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
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


def _amex_row(y: float, txn_day: str, process_day: str, description: str, amount: str, cr: bool = False):
    tokens = [
        (14.4, y, "Aug"),
        (32.6, y, txn_day),
        (57.6, y, "Aug"),
        (75.8, y, process_day),
        (100.8, y, description),
        (504.2, y - 0.7, amount),
    ]
    if cr:
        tokens.append((518.9, y - 12.0, "CR"))
    return tokens


def amex_pages() -> list[list[tuple[float, float, str]]]:
    """Synthetic Amex-shaped pages: summary, monthly table, annual summary."""
    pages: list[list[tuple[float, float, str]]] = []
    pages.append(
        [
            (14.4, 749.3, "Statement of Account"),
            (14.4, 727.2, "Prepared for"),
            (519.6, 727.2, "Date"),
            (14.4, 716.4, "TEST CARDHOLDER"),
            (486.2, 716.4, "10"),
            (497.3, 716.4, "/"),
            (502.6, 716.4, "09"),
            (515.3, 716.4, "/"),
            (520.8, 716.4, "26"),
            (14.4, 640.0, "Previous Balance"),
            (400.0, 640.0, "£"),
            (415.0, 640.0, "300.00"),
            (14.4, 620.0, "New Balance"),
            (400.0, 620.0, "£"),
            (415.0, 620.0, "842.25"),
            (14.4, 600.0, "Payments and Credits"),
            (400.0, 600.0, "£"),
            (415.0, 600.0, "100.00"),
        ]
    )
    table = [
        (14.4, 529.2, "Transaction"),
        (57.6, 529.2, "Process"),
        (14.4, 521.3, "Date"),
        (57.6, 521.3, "Date"),
        (100.8, 521.3, "Transaction Details"),
        (504.2, 519.6, "Amount"),
        (529.2, 519.6, "£"),
    ]
    table += _amex_row(502.6, "22", "22", "PAYMENT RECEIVED - THANK YOU", "100.00", cr=True)
    table += _amex_row(471.1, "15", "15", "COFFEE MERCHANT LONDON", "12.00")
    table += _amex_row(451.9, "15", "15", "BOOK STORE LONDON", "30.00")
    table += _amex_row(432.7, "21", "21", "TRAVEL SITE INTERNET", "500.25")
    table += _amex_row(413.5, "27", "28", "AIRPORT TRANSFER LONDON", "100.00")
    # FX detail lines belong to the row above, not to new transactions.
    table += [
        (100.8, 400.0, "AIRPORT TRANSFER LONDON"),
        (100.8, 392.0, "Exchange Rate 1.2345"),
        (100.8, 384.0, "+"),
        (100.8, 376.0, "Nonsterling Transaction Fee 1.50"),
    ]
    pages.append(table)
    pages.append(
        [
            (14.4, 749.3, "Annual Summary"),
            (14.4, 720.0, "Total debits for the year"),
            (400.0, 720.0, "£"),
            (415.0, 720.0, "5,000.00"),
            (14.4, 700.0, "Total credits for the year"),
            (400.0, 700.0, "£"),
            (415.0, 700.0, "1,000.00"),
        ]
    )
    return pages


def amex_pdf() -> bytes:
    return positioned_statement_pdf(amex_pages())


def amex_tokens() -> list[tuple[float, float, str]]:
    return [token for page in amex_pages() for token in page]


def extract_positioned_token_pages(data: bytes) -> list[list[tuple[float, float, str]]]:
    reader = pypdf.PdfReader(io.BytesIO(data))
    pages: list[list[tuple[float, float, str]]] = []
    for page in reader.pages:
        tokens: list[tuple[float, float, str]] = []

        def visitor(text, cm, tm, font_dict, font_size):
            cleaned = (text or "").strip()
            if cleaned:
                tokens.append((round(tm[4], 1), round(tm[5], 1), cleaned))

        page.extract_text(visitor_text=visitor)
        pages.append(tokens)
    return pages


def extract_positioned_tokens(data: bytes) -> list[tuple[float, float, str]]:
    return [token for page in extract_positioned_token_pages(data) for token in page]
