"""Behavioral tests for the Lloyds Current interpretation contract.

Expected values are recorded from hand arithmetic in the fixture docstring and
the independently checked balance equations, not from parser output.
"""

from datetime import date

from django.test import SimpleTestCase

from interpretation.lloyds_current import parse
from ledger.tests.statement_fixtures import (
    extract_text,
    lloyds_current_pages,
    lloyds_current_pdf,
    lloyds_current_text,
)


def text_with(*replacements: tuple[str, str]) -> str:
    text = lloyds_current_text()
    for old, new in replacements:
        assert old in text, old
        text = text.replace(old, new, 1)
    return text


class ExtractionTests(SimpleTestCase):
    def test_extracts_each_dated_row_with_direction_and_balance(self):
        result = parse(lloyds_current_text())

        self.assertTrue(result.recognised)
        self.assertEqual(result.account_kind_hint, "current")
        self.assertEqual(
            [
                (
                    row.posted_on,
                    row.description,
                    row.transaction_type,
                    row.amount_pence,
                    row.balance_pence,
                )
                for row in result.rows
            ],
            [
                (date(2026, 8, 1), "COFFEE SHOP", "Card payment", -320, 119680),
                (date(2026, 8, 2), "SALARY ACME LTD", "Bank credit", 250000, 369680),
                (date(2026, 8, 3), "RENT PAYMENT", "DD", -95000, 274680),
                (date(2026, 8, 4), "CORNER STORE", "Card payment", -1244, 273436),
                (date(2026, 8, 5), "REFUND CORNER STORE", "Refund", 1244, 274680),
                (date(2026, 8, 6), "CASH WITHDRAWAL", "Cash withdrawal", -10000, 264680),
            ],
        )
        self.assertEqual([row.page for row in result.rows], [1, 1, 1, 1, 2, 2])
        self.assertEqual([row.row for row in result.rows], [1, 2, 3, 4, 1, 2])

    def test_reconciles_opening_closing_and_stated_totals(self):
        result = parse(lloyds_current_text())

        self.assertTrue(result.reconciled)
        self.assertEqual(result.issues, [])
        self.assertEqual(result.opening_pence, 120000)
        self.assertEqual(result.closing_pence, 264680)
        self.assertEqual(result.money_in_pence, 251244)
        self.assertEqual(result.money_out_pence, 106564)

    def test_balances_record_the_statement_anchors(self):
        result = parse(lloyds_current_text())

        self.assertEqual(
            [(balance.kind, balance.amount_pence) for balance in result.balances],
            [("opening", 120000), ("closing", 264680)],
        )

    def test_pdf_text_extraction_reaches_the_same_rows(self):
        from_pdf = parse(extract_text(lloyds_current_pdf()))

        self.assertTrue(from_pdf.reconciled)
        self.assertEqual(
            [(row.posted_on, row.amount_pence) for row in from_pdf.rows],
            [(row.posted_on, row.amount_pence) for row in parse(lloyds_current_text()).rows],
        )

    def test_accessibility_labels_and_repeated_headers_are_ignored(self):
        pages = lloyds_current_pages()
        noisy = [line for page in pages for line in page]
        noisy.insert(7, "Column")
        noisy.append("Money In (£).")

        result = parse("\n".join(noisy))

        self.assertTrue(result.recognised)
        self.assertEqual(len(result.rows), 6)
        self.assertTrue(result.reconciled)


class RejectionTests(SimpleTestCase):
    def test_unsupported_text_is_not_recognised(self):
        result = parse("Some other bank\nNothing here to interpret\n")

        self.assertFalse(result.recognised)
        self.assertEqual(result.rows, [])

    def test_malformed_transaction_row_is_reported_not_guessed(self):
        result = parse(text_with(("Money Out (£)\n3.20.", "Money Out (£)\n3,2O.")))

        self.assertFalse(result.reconciled)
        self.assertIn("malformed_transaction_row", [issue.code for issue in result.issues])

    def test_running_balance_disagreement_is_reported(self):
        result = parse(text_with(("Balance (£)\n3,696.80.", "Balance (£)\n3,697.80.")))

        self.assertFalse(result.reconciled)
        self.assertIn("running_balance_mismatch", [issue.code for issue in result.issues])

    def test_stated_total_disagreement_is_reported(self):
        result = parse(text_with(("Money Out.\n1,065.64.", "Money Out.\n1,000.00.")))

        self.assertFalse(result.reconciled)
        self.assertIn("totals_mismatch", [issue.code for issue in result.issues])

    def test_row_outside_the_statement_period_is_reported(self):
        result = parse(text_with(("01 Aug 26.", "01 Sep 26.")))

        self.assertFalse(result.reconciled)
        self.assertIn("date_outside_period", [issue.code for issue in result.issues])

    def test_missing_closing_anchor_is_reported(self):
        result = parse(text_with(("Balance on 31 August 2026.\n2,646.80.\n", "")))

        self.assertFalse(result.reconciled)
        self.assertIn("missing_closing_balance", [issue.code for issue in result.issues])
