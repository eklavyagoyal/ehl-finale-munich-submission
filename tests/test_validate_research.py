"""Regression checks for evidence identity, claim provenance, and malformed inputs."""

import importlib.util
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_research", ROOT / "scripts/validate_research.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ResearchValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="bmw-research-test-")
        self.addCleanup(self.temp.cleanup)
        self.batch_root = Path(self.temp.name) / "batches"
        shutil.copytree(ROOT / "research/examples", self.batch_root)

    def edit(self, relative_path, change, jsonl=False):
        path = self.batch_root / relative_path
        documents = [json.loads(line) for line in path.read_text().splitlines()] if jsonl else [json.loads(path.read_text())]
        change(documents[0])
        path.write_text("".join(json.dumps(d) + "\n" for d in documents))

    def test_multiple_claims_keep_one_parent_review(self):
        self.assertEqual(VALIDATOR.validate_batches(self.batch_root), (4, 4, 2))
        claims = [json.loads(line) for line in (self.batch_root / "social/claims.jsonl").read_text().splitlines()]
        self.assertEqual(len({claim["record_id"] for claim in claims}), 1)
        record = json.loads((self.batch_root / "social/records.jsonl").read_text())
        self.assertEqual(record["locator"]["kind"], "table")
        self.assertEqual(record["locator"]["native_id"], record["source_fields"]["ReviewID"])

    def test_rejects_fabricated_quote(self):
        self.edit("social/claims.jsonl", lambda d: d.update(quotes=["An invented quote."]), jsonl=True)
        with self.assertRaisesRegex(ValueError, "exact substring"):
            VALIDATOR.validate_batches(self.batch_root)

    def test_rejects_missing_or_cross_batch_claim_parent(self):
        for parent in ("missing-review", "example-feedback-001-v1"):
            with self.subTest(parent=parent):
                self.edit("social/claims.jsonl", lambda d: d.update(record_id=parent), jsonl=True)
                with self.assertRaisesRegex(ValueError, "missing record or different batch"):
                    VALIDATOR.validate_batches(self.batch_root)

    def test_rejects_duplicate_observation_even_with_different_snapshot_id(self):
        path = self.batch_root / "social/records.jsonl"
        record = json.loads(path.read_text())
        record["record_id"] = "different-snapshot-same-observation"
        with path.open("a") as stream:
            stream.write(json.dumps(record) + "\n")
        with self.assertRaisesRegex(ValueError, "duplicate observation"):
            VALIDATOR.validate_batches(self.batch_root)

    def test_rejects_unknown_subject_and_inaccurate_manifest_count(self):
        self.edit("social/records.jsonl", lambda d: d.update(subject_ids=["unresolved:app"]), jsonl=True)
        with self.assertRaisesRegex(ValueError, "unknown subject_id"):
            VALIDATOR.validate_batches(self.batch_root)
        self.edit("social/records.jsonl", lambda d: d.update(subject_ids=[]), jsonl=True)
        self.edit("social/source.json", lambda d: d.update(normalized_record_count=2))
        with self.assertRaisesRegex(ValueError, "normalized_record_count"):
            VALIDATOR.validate_batches(self.batch_root)

    def test_rejects_percentage_and_proportion_scale_mistakes(self):
        for statistic, value in (("percentage", 101), ("proportion", 1.2)):
            with self.subTest(statistic=statistic):
                self.edit("bmw-study/records.jsonl", lambda d: d["metric"].update(statistic=statistic, value=value), jsonl=True)
                with self.assertRaises(ValueError):
                    VALIDATOR.validate_batches(self.batch_root)

    def test_requires_llm_run_provenance(self):
        self.edit("social/claims.jsonl", lambda d: d["producer"].update(method="llm"), jsonl=True)
        with self.assertRaises(ValueError):
            VALIDATOR.validate_batches(self.batch_root)

    def test_rejects_nonfinite_numbers_and_duplicate_json_keys(self):
        for payload in ('{"x":NaN}', '{"x":Infinity}', '{"x":1e9999}', '{"x":1,"x":2}'):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "invalid JSON"):
                VALIDATOR.parse_json(payload, "synthetic-input")

    def test_rejects_empty_collection_and_blank_jsonl(self):
        with self.assertRaisesRegex(ValueError, "no source.json"):
            VALIDATOR.validate_batches(Path(self.temp.name) / "missing")
        (self.batch_root / "social/records.jsonl").write_text("\n")
        with self.assertRaisesRegex(ValueError, "blank JSONL line"):
            VALIDATOR.validate_batches(self.batch_root)

    def test_rejects_duplicate_catalog_identifiers(self):
        path = Path(self.temp.name) / "catalog.json"
        path.write_text(json.dumps({"entities": [{"entity_id": "app:1"}, {"entity_id": "app:1"}]}))
        with self.assertRaisesRegex(ValueError, "duplicate entity_id"):
            VALIDATOR.catalog_ids(path, "entities", "entity_id")


if __name__ == "__main__":
    unittest.main()
