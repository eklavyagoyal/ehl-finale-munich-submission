"""Offline tests for the research-contract export, on a tiny temporary warehouse."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scrapers import export_research, warehouse


def review(review_id, content, rating=4):
    return {"store": "app_store", "store_app_id": "123", "market": "de", "review_id": review_id,
            "datetime": datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc), "content": content,
            "rating": rating, "app_version": "1.0"}


class ExportResearchTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        patcher = mock.patch.object(warehouse, "WAREHOUSE_DIR", self.root / "warehouse")
        patcher.start()
        self.addCleanup(patcher.stop)
        # Artifact paths are stored relative to the repo root.
        patcher = mock.patch.object(export_research, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.load([review("app_store:1", "Please add a widget"), review("app_store:2", "  ", rating=1)])

    def load(self, reviews):
        app = {"store": "app_store", "store_app_id": "123", "app_name": "My App", "bundle_id": "x", "developer": "d"}
        for name, rows in warehouse.build_tables(reviews, [app]).items():
            warehouse.upsert(name, rows)

    def export(self):
        out = self.root / "out"
        export_research.export(out, collector="tester", channels=["app_store"])
        batch = next((out / "social").iterdir())
        source = json.loads((batch / "source.json").read_text())
        records = [json.loads(line) for line in (batch / "records.jsonl").read_text().splitlines()]
        return batch, source, records

    def test_batch_links_and_skips_rating_only_reviews(self):
        batch, source, records = self.export()
        self.assertEqual(len(records), 1)
        self.assertEqual(source["normalized_record_count"], 1)
        self.assertEqual(source["sampling"]["retrieved_count"], 2)
        self.assertTrue(any("rating-only" in item for item in source["sampling"]["limitations"]))
        self.assertEqual(source["dataset_key"], "app_store:123:DE")
        self.assertIsNone(source["export_permissions"]["git"])

        record = records[0]
        self.assertEqual(record["source_id"], source["source_id"])
        self.assertEqual(record["dedup_key"], "app_store:123:DE:1")
        self.assertEqual(record["markets"], ["DE"])
        self.assertEqual(record["source_fields"]["Rating"], 4)
        self.assertIsInstance(record["source_fields"]["DimAppID"], str)  # BIGINTs as strings
        self.assertTrue((batch / "notes.md").exists())

    def test_record_ids_are_stable_and_change_with_text(self):
        _, _, first = self.export()
        _, _, again = self.export()
        self.assertEqual(first[0]["record_id"], again[0]["record_id"])

        self.load([review("app_store:1", "Please add a home screen widget")])
        _, _, edited = self.export()
        self.assertEqual(edited[0]["dedup_key"], first[0]["dedup_key"])
        self.assertNotEqual(edited[0]["record_id"], first[0]["record_id"])


if __name__ == "__main__":
    unittest.main()
