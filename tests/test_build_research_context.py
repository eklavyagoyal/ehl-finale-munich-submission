"""Checks for safe eligibility, snapshot deduplication, and review frequency."""

import hashlib
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_research_context as CONTEXT
from validate_research import load_batches


class ContextExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="bmw-context-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.batches = self.root / "batches"
        shutil.copytree(ROOT / "research/examples", self.batches)

    def json(self, path):
        return json.loads(path.read_text())

    def lines(self, path):
        return [json.loads(line) for line in path.read_text().splitlines()]

    def write_lines(self, path, rows):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def make_reviewed(self):
        # Exercise real-source gates using temporary synthetic test content only.
        for path in self.batches.rglob("source.json"):
            source = self.json(path)
            source.update(is_example=False, review_status="accepted")
            source["provenance"]["origin"] = "third_party"
            path.write_text(json.dumps(source))
        for path in self.batches.rglob("claims.jsonl"):
            rows = self.lines(path)
            for claim in rows:
                claim["review_status"] = "accepted"
            self.write_lines(path, rows)

    def second_review_snapshot(self, timestamp, dataset=None, text=None):
        destination = self.batches / "social-second"
        shutil.copytree(self.batches / "social", destination)
        path = destination / "source.json"
        source = self.json(path)
        source.update(source_id="second-source", collected_at=timestamp)
        if dataset:
            source["dataset_key"] = dataset
        path.write_text(json.dumps(source))
        path = destination / "records.jsonl"
        record = self.json(path)
        record.update(record_id="second-review", source_id="second-source")
        if text:
            record["text_original"] = text
        self.write_lines(path, [record])
        path = destination / "claims.jsonl"
        claims = self.lines(path)
        for claim in claims:
            claim.update(record_id="second-review", claim_id=claim["claim_id"] + "-second")
        self.write_lines(path, claims)

    def test_demo_retains_all_targets_and_is_explicitly_synthetic(self):
        packet = CONTEXT.build_context(self.batches, demo=True, run_id="test-demo")
        self.assertTrue(packet["run_manifest"]["is_demo"])
        self.assertEqual(packet["scope"]["target_model_ids"], ["bmw:F70", "bmw:G60", "bmw:G70"])
        self.assertEqual(packet["coverage"]["exported_record_count"], 4)
        self.assertEqual(packet["coverage"]["feedback_review_count"], 2)
        self.assertEqual(packet["coverage"]["records_with_direct_target_subject"], {"bmw:F70": 1, "bmw:G60": 1, "bmw:G70": 0})
        self.assertEqual(sum(row["record_count"] for row in packet["coverage"]["record_counts_by_scope"]), 4)

    def test_normal_export_rejects_fixtures_and_unreviewed_sources(self):
        with self.assertRaisesRegex(ValueError, "No eligible evidence"):
            CONTEXT.build_context(self.batches)
        self.make_reviewed()
        for path in self.batches.rglob("source.json"):
            source = self.json(path)
            source["review_status"] = "pending"
            path.write_text(json.dumps(source))
        with self.assertRaisesRegex(ValueError, "No eligible evidence"):
            CONTEXT.build_context(self.batches)

    def test_unconfirmed_permission_excludes_source_and_its_claims(self):
        self.make_reviewed()
        path = self.batches / "social/source.json"
        source = self.json(path)
        source["export_permissions"]["external_llm"] = None
        path.write_text(json.dumps(source))
        packet = CONTEXT.build_context(self.batches)
        self.assertEqual(packet["coverage"]["exported_record_count"], 3)
        self.assertEqual(packet["claims"], [])
        self.assertIn("external_llm_permission_not_confirmed", packet["coverage"]["excluded_sources"][0]["reasons"])

    def test_latest_snapshot_keeps_review_frequency_unchanged(self):
        self.make_reviewed()
        self.second_review_snapshot("2026-10-11T10:00:00Z")
        packet = CONTEXT.build_context(self.batches)
        self.assertEqual(packet["coverage"]["input_record_count"], 5)
        self.assertEqual(packet["coverage"]["exported_record_count"], 4)
        self.assertEqual(len(packet["coverage"]["superseded_records"]), 1)
        self.assertEqual({claim["record_id"] for claim in packet["claims"]}, {"second-review"})
        self.assertTrue(all(row["mention_review_count"] == 1 for row in packet["feature_frequency"]["by_feature"]))

    def test_collection_timestamps_compare_instants_including_offsets(self):
        self.make_reviewed()
        self.second_review_snapshot("2026-10-10T11:00:00+02:00")
        packet = CONTEXT.build_context(self.batches)
        self.assertIn("example-review-001-v1", {record["record_id"] for record in packet["records"]})
        self.assertNotIn("second-review", {record["record_id"] for record in packet["records"]})

    def test_equal_time_conflicting_snapshots_need_review(self):
        self.make_reviewed()
        original = self.json(self.batches / "social/records.jsonl")["text_original"]
        self.second_review_snapshot("2026-10-10T12:00:00+02:00", text=original + " An additional statement.")
        with self.assertRaisesRegex(ValueError, "Conflicting snapshots"):
            CONTEXT.build_context(self.batches)

    def test_same_native_identity_in_distinct_datasets_is_not_merged(self):
        self.make_reviewed()
        self.second_review_snapshot("2026-10-11T10:00:00Z", dataset="different:review-provider")
        packet = CONTEXT.build_context(self.batches)
        self.assertEqual(packet["coverage"]["exported_record_count"], 5)
        self.assertTrue(all(row["mention_review_count"] == 2 for row in packet["feature_frequency"]["by_feature"]))

    def test_multiple_claims_for_one_feature_count_one_review(self):
        self.make_reviewed()
        path = self.batches / "social/claims.jsonl"
        claims = self.lines(path)
        alias = dict(claims[0], claim_id="heating-alias", feature_label="Cabin preconditioning")
        self.write_lines(path, claims + [alias])
        packet = CONTEXT.build_context(self.batches)
        heating = next(row for row in packet["feature_frequency"]["by_feature"] if row["feature_key"] == "remote_climate_scheduling")
        self.assertEqual(heating["mention_review_count"], 1)
        self.assertEqual(heating["request_review_count"], 1)
        cohort = next(row for row in packet["feature_frequency"]["by_cohort"] if row["feature_key"] == "remote_climate_scheduling")
        self.assertEqual(cohort["feedback_review_count"], 1)
        self.assertEqual(cohort["mention_share_of_collected_reviews"], 1)
        self.assertEqual(cohort["subject_ids"], [])

    def test_pending_claims_do_not_become_reviewed_frequencies(self):
        self.make_reviewed()
        path = self.batches / "social/claims.jsonl"
        claims = self.lines(path)
        claims[0]["review_status"] = "pending"
        self.write_lines(path, claims)
        packet = CONTEXT.build_context(self.batches)
        self.assertEqual(len(packet["claims"]), 1)
        self.assertEqual(packet["feature_frequency"]["by_feature"][0]["request_review_count"], 0)
        self.assertEqual(packet["coverage"]["omitted_claims"][0]["reason"], "claim_not_accepted")

    def test_official_availability_is_not_counted_as_customer_feedback(self):
        self.make_reviewed()
        record = self.json(self.batches / "competitor/records.jsonl")
        claim = self.lines(self.batches / "social/claims.jsonl")[0]
        claim.update(claim_id="official-claim", record_id=record["record_id"], claim_type="feature_present", quotes=[record["text_original"]])
        self.write_lines(self.batches / "competitor/claims.jsonl", [claim])
        packet = CONTEXT.build_context(self.batches)
        self.assertEqual(len(packet["claims"]), 3)
        heating = next(row for row in packet["feature_frequency"]["by_feature"] if row["feature_key"] == "remote_climate_scheduling")
        self.assertEqual(heating["mention_review_count"], 1)

    def test_fingerprints_match_the_bytes_parsed(self):
        documents = load_batches(self.batches)
        for path, digest in documents["fingerprints"].items():
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_output_is_atomic_preserves_previous_runs_and_obeys_limits(self):
        with patch.object(CONTEXT, "ROOT", self.root):
            output = self.root / "outputs/research/test/context.json"
            CONTEXT.write_context({"test": 1}, output)
            with self.assertRaises(FileExistsError):
                CONTEXT.write_context({"test": 2}, output)
            self.assertEqual(self.json(output), {"test": 1})
            oversized = self.root / "outputs/research/oversized/context.json"
            with self.assertRaisesRegex(ValueError, "max-bytes"):
                CONTEXT.write_context({"text": "a" * 100}, oversized, max_bytes=10)
            self.assertFalse(oversized.exists())
            with self.assertRaisesRegex(ValueError, "ignored outputs"):
                CONTEXT.write_context({"test": 1}, self.root / "research/leaked.json")


if __name__ == "__main__":
    unittest.main()
