"""Behavioral tests for the isolated local advisory inference integration."""

import json
from unittest import mock
import urllib.error
from django.test import SimpleTestCase

from worker.advisory import (
    AdvisoryClassification,
    AdvisoryFormatError,
    AdvisorySuggestion,
    AdvisoryUnavailableError,
    LocalInferenceClient,
)


class AdvisoryValidationTests(SimpleTestCase):
    def test_valid_suggestion_roundtrips_and_preserves_provenance(self):
        payload = {
            "version": 1,
            "classification": "spending",
            "confidence": 0.92,
            "explanation": "Card payment at a coffee shop.",
            "model": "qwen2.5:3b-instruct",
            "prompt_version": "v1",
        }
        suggestion = AdvisorySuggestion.from_dict(payload)
        self.assertEqual(suggestion.classification, AdvisoryClassification.SPENDING)
        self.assertEqual(suggestion.confidence, 0.92)
        self.assertEqual(suggestion.to_dict(), payload)

    def test_unsupported_version_abstains(self):
        with self.assertRaisesRegex(ValueError, "Unsupported advisory schema version"):
            AdvisorySuggestion.from_dict(
                {
                    "version": 99,
                    "classification": "spending",
                    "confidence": 0.5,
                    "explanation": "x",
                    "model": "m",
                }
            )

    def test_unknown_classification_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown advisory classification"):
            AdvisorySuggestion.from_dict(
                {
                    "version": 1,
                    "classification": "loan",
                    "confidence": 0.5,
                    "explanation": "x",
                    "model": "m",
                }
            )

    def test_missing_explanation_or_out_of_range_confidence_is_rejected(self):
        for payload, message in (
            (
                {
                    "version": 1,
                    "classification": "income",
                    "confidence": 0.7,
                    "explanation": "",
                    "model": "m",
                },
                "Explanation is required",
            ),
            (
                {
                    "version": 1,
                    "classification": "income",
                    "confidence": 1.5,
                    "explanation": "x",
                    "model": "m",
                },
                "Confidence out of range",
            ),
            (
                {
                    "version": 1,
                    "classification": "income",
                    "confidence": 0.7,
                    "explanation": "x",
                    "model": "",
                },
                "Model is required",
            ),
        ):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, message):
                    AdvisorySuggestion.from_dict(payload)


class LocalInferenceClientTests(SimpleTestCase):
    def setUp(self):
        self.client = LocalInferenceClient(
            "http://127.0.0.1:11434", model="qwen2.5:3b-instruct", timeout_seconds=2.0
        )

    def mock_urlopen(self, body, status=200):
        response = mock.MagicMock()
        response.status = status
        response.read.return_value = body
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        return mock.patch("urllib.request.urlopen", return_value=response)

    def test_valid_model_response_returns_validated_suggestion(self):
        model_body = json.dumps(
            {
                "classification": "transfer",
                "confidence": 0.88,
                "explanation": "Transferred between savings and current.",
            }
        )
        body = json.dumps({"response": model_body}).encode()

        with self.mock_urlopen(body):
            suggestion = self.client.suggest_classification(
                "TRANSFER TO SAVINGS", -50000, "current"
            )

        self.assertEqual(suggestion.classification, AdvisoryClassification.TRANSFER)
        self.assertEqual(suggestion.confidence, 0.88)
        self.assertEqual(suggestion.model, "qwen2.5:3b-instruct")
        self.assertEqual(suggestion.prompt_version, "v1")

    def test_unavailable_runtime_raises_unavailable_not_format_error(self):
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            with self.assertRaisesRegex(AdvisoryUnavailableError, "Failed to connect"):
                self.client.suggest_classification("SHOP", -100, "current")

    def test_malformed_model_json_raises_format_error(self):
        body = json.dumps({"response": "{not-json"}).encode()
        with self.mock_urlopen(body):
            with self.assertRaisesRegex(AdvisoryFormatError, "Malformed JSON"):
                self.client.suggest_classification("SHOP", -100, "current")

    def test_invented_classification_from_model_raises_format_error(self):
        model_body = json.dumps(
            {"classification": "loan", "confidence": 0.5, "explanation": "guess"}
        )
        body = json.dumps({"response": model_body}).encode()
        with self.mock_urlopen(body):
            with self.assertRaisesRegex(AdvisoryFormatError, "failed validation"):
                self.client.suggest_classification("SHOP", -100, "current")

    def test_http_error_status_is_unavailable(self):
        with self.mock_urlopen(b"{}", status=500):
            with self.assertRaisesRegex(AdvisoryUnavailableError, "HTTP error 500"):
                self.client.suggest_classification("SHOP", -100, "current")
