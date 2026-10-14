"""Offline invariant tests; every website and observation here is synthetic."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_audit.py"
SPEC = importlib.util.spec_from_file_location("audit_validator", SCRIPT)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class AuditValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.package = self.root / "audit.json"
        (self.root / "capture.txt").write_text("SYNTHETIC: visible Download button", encoding="utf-8")
        self.scope = {"site": "example.invalid", "locale": "en", "page": "/", "device": "desktop"}
        self.data = {
            "schema_version": 1, "run_id": "synthetic-test",
            "as_of": "2026-10-14T12:00:00+08:00",
            "evidence": [{
                "id": "E1", "claim": "SYNTHETIC: the page displays a download button",
                "kind": "observation", "status": "current",
                "source": "https://example.invalid/", "observed_at": "2026-10-14T11:00:00+08:00",
                "method": "synthetic rendered observation", "scope": dict(self.scope),
                "artifact": "capture.txt", "derived_from": [],
            }],
            "coverage": [{"scope": {**self.scope, "check": "visual"}, "status": "verified",
                          "evidence_ids": ["E1"], "note": "Synthetic desktop only; mobile not tested."}],
        }

    def tearDown(self):
        self.temp.cleanup()

    def check_valid(self, data):
        self.assertEqual([], VALIDATOR.validate(data, self.package))

    def check_invalid(self, data):
        errors = VALIDATOR.validate(data, self.package)
        self.assertTrue(errors, "Invalid evidence must not pass structural validation")
        self.assertTrue(all(isinstance(error, str) for error in errors))

    def test_current_capture(self):
        self.check_valid(self.data)

    def test_official_claim_is_not_product_verification(self):
        self.data["evidence"][0]["kind"] = "official_claim"
        self.check_valid(self.data)  # Kind must remain official_claim after validation.
        self.assertEqual("official_claim", self.data["evidence"][0]["kind"])

    def test_historical_and_unverified_gaps_are_legitimate(self):
        for status in ("historical", "unverified"):
            with self.subTest(status=status):
                data = copy.deepcopy(self.data)
                data["evidence"][0].update(status=status, artifact=None)
                if status == "unverified":
                    data["evidence"][0]["observed_at"] = None
                data["coverage"][0].update(status="not_tested", evidence_ids=[])
                self.check_valid(data)

    def test_historical_date_precision_is_preserved(self):
        self.data["evidence"][0].update(status="historical", artifact=None, observed_at="2026-07-22")
        self.data["coverage"][0].update(status="partial")
        self.check_valid(self.data)
        self.assertEqual("2026-07-22", self.data["evidence"][0]["observed_at"])

    def test_unknown_historical_time_requires_explanation(self):
        self.data["evidence"][0].update(status="historical", artifact=None, observed_at=None)
        self.data["coverage"][0].update(status="partial")
        self.check_invalid(self.data)
        self.data["evidence"][0]["time_note"] = "Original synthetic record has no observation date."
        self.check_valid(self.data)

    def test_current_evidence_still_requires_precise_time(self):
        self.data["evidence"][0]["observed_at"] = "2026-10-14"
        self.check_invalid(self.data)

    def test_future_historical_calendar_date_is_rejected(self):
        self.data["evidence"][0].update(status="historical", observed_at="2026-10-15")
        self.data["coverage"][0].update(status="partial")
        self.check_invalid(self.data)

    def test_empty_evidence_with_explicit_blocker(self):
        self.data["evidence"] = []
        self.data["coverage"][0].update(status="blocked", evidence_ids=[], note="Synthetic access denied")
        self.check_valid(self.data)

    def test_missing_current_capture(self):
        self.data["evidence"][0]["artifact"] = "missing.png"
        self.check_invalid(self.data)

    def test_artifact_escape_and_directory(self):
        for artifact in ("../outside.txt", str(self.root / "capture.txt"), "."):
            with self.subTest(artifact=artifact):
                data = copy.deepcopy(self.data)
                data["evidence"][0]["artifact"] = artifact
                self.check_invalid(data)

    def test_historical_artifact_must_be_file_if_supplied(self):
        self.data["evidence"][0].update(status="historical", artifact=".")
        self.data["coverage"][0].update(status="partial")
        self.check_invalid(self.data)

    def test_future_dates_for_all_statuses(self):
        for status in ("current", "historical", "unverified"):
            with self.subTest(status=status):
                data = copy.deepcopy(self.data)
                data["evidence"][0].update(status=status, observed_at="2026-10-15T11:00:00+08:00")
                data["coverage"][0]["status"] = "partial"
                self.check_invalid(data)

    def test_times_require_timezone(self):
        self.data["evidence"][0]["observed_at"] = "2026-10-14T11:00:00"
        self.check_invalid(self.data)

    def test_duplicate_ids(self):
        self.data["evidence"].append(copy.deepcopy(self.data["evidence"][0]))
        self.check_invalid(self.data)

    def test_unknown_reference(self):
        self.data["coverage"][0]["evidence_ids"] = ["UNKNOWN"]
        self.check_invalid(self.data)

    def test_unknown_reference_in_incomplete_coverage(self):
        for status in ("partial", "blocked", "not_tested"):
            with self.subTest(status=status):
                data = copy.deepcopy(self.data)
                data["coverage"][0].update(status=status, evidence_ids=["UNKNOWN"])
                self.check_invalid(data)

    def test_self_reference(self):
        self.data["evidence"][0].update(kind="reviewer_inference", derived_from=["E1"])
        self.check_invalid(self.data)

    def test_dependency_cycle(self):
        second = copy.deepcopy(self.data["evidence"][0])
        second.update(id="E2", kind="reviewer_inference", derived_from=["E1"])
        self.data["evidence"][0].update(kind="reviewer_inference", derived_from=["E2"])
        self.data["evidence"].append(second)
        self.check_invalid(self.data)

    def test_inference_needs_underlying_evidence(self):
        self.data["evidence"][0]["kind"] = "reviewer_inference"
        self.check_invalid(self.data)

    def test_verified_requires_current(self):
        self.data["evidence"][0]["status"] = "historical"
        self.check_invalid(self.data)

    def test_requirement_cannot_prove_a_page_was_tested(self):
        self.data["evidence"][0]["kind"] = "user_requirement"
        self.check_invalid(self.data)

    def test_inference_cannot_prove_a_page_was_tested(self):
        second = copy.deepcopy(self.data["evidence"][0])
        second["id"] = "E2"
        self.data["evidence"].append(second)
        self.data["evidence"][0].update(kind="reviewer_inference", derived_from=["E2"])
        self.check_invalid(self.data)

    def test_invalid_source_url_reports_error(self):
        self.data["evidence"][0]["source"] = "https://["
        self.check_invalid(self.data)

    def test_verified_requires_matching_scope(self):
        for key in ("site", "locale", "page", "device"):
            with self.subTest(key=key):
                data = copy.deepcopy(self.data)
                data["coverage"][0]["scope"][key] = "different"
                self.check_invalid(data)

    def test_mixed_scope_cannot_hide_behind_one_good_reference(self):
        second = copy.deepcopy(self.data["evidence"][0])
        second["id"] = "E2"
        second["scope"]["device"] = "mobile"
        self.data["evidence"].append(second)
        self.data["coverage"][0]["evidence_ids"].append("E2")
        self.check_invalid(self.data)

    def test_duplicate_coverage_does_not_inflate_count(self):
        self.data["coverage"].append(copy.deepcopy(self.data["coverage"][0]))
        self.check_invalid(self.data)

    def test_noninteger_schema_version(self):
        for version in (True, 1.0, "1"):
            with self.subTest(version=version):
                data = copy.deepcopy(self.data)
                data["schema_version"] = version
                self.check_invalid(data)

    def test_required_nullable_fields_still_must_be_present(self):
        for field in ("observed_at", "artifact"):
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data["evidence"][0]["status"] = "unverified"
                data["coverage"][0]["status"] = "not_tested"
                del data["evidence"][0][field]
                self.check_invalid(data)

    def test_malformed_field_types_return_errors(self):
        for field, value in (("kind", []), ("status", {}), ("scope", []),
                             ("derived_from", [{}]), ("id", [])):
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data["evidence"][0][field] = value
                self.check_invalid(data)
        for field, value in (("scope", []), ("status", []), ("evidence_ids", [{}])):
            with self.subTest(coverage_field=field):
                data = copy.deepcopy(self.data)
                data["coverage"][0][field] = value
                self.check_invalid(data)

    def test_cli_reports_gap_without_claiming_completion(self):
        self.data["coverage"][0].update(status="not_tested", evidence_ids=[])
        self.package.write_text(json.dumps(self.data), encoding="utf-8")
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), str(self.package)], capture_output=True, encoding="utf-8")
        self.assertEqual(0, result.returncode, result.stderr)
        # Test behavior: structured validation does not assert all cells are complete.
        self.assertIn("not_tested", result.stdout)

    def test_cli_rejects_malformed_json_without_traceback(self):
        self.package.write_text("not json", encoding="utf-8")
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), str(self.package)], capture_output=True, encoding="utf-8")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_rejects_invalid_encoding_without_traceback(self):
        self.package.write_bytes(b"\xff\xfeinvalid")
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), str(self.package)], capture_output=True, encoding="utf-8")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
