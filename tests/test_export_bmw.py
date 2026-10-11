"""Checks for the BMW workbook exporter on small synthetic workbooks (no BMW content)."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXPORT = load("export_bmw", ROOT / "scripts/export_bmw.py")
VALIDATOR = load("validate_research", ROOT / "scripts/validate_research.py")

FEEDBACK_HEADER = ["ID", "Source", "Brand", "Sales Description", "Country", "Derivate (e-code)", "Engine Type",
                   "Feedback Type", "Customer Feedback", "Vfc level2 3 Name", "Vfc level2 Name", "Vfc level3 Name"]


def feedback_row(feedback_id, text, topic=None, feedback_type=None, nature=None, country="US", engine="BEVE"):
    combined = f"{topic} : {nature}" if topic and nature else topic
    return [feedback_id, "Source A", "[BMW]", "[BMW 5 Series]", country, "G60", engine, feedback_type,
            text, combined, topic, nature]


def save(path, sheets):
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    workbook.save(path)


class BmwExportTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="bmw-export-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.data = self.base / "data"
        self.data.mkdir()
        self.output = self.base / "out"
        self.catalog = self.base / "features.json"
        shutil.copy(ROOT / "research/catalog/features.json", self.catalog)
        self.feedback_rows = [
            feedback_row("G60-0001", "SYNTHETIC: I want a hover mode and the seats are comfy.", "Synthetic hover mode",
                         "Wants", "Customer request: function"),
            feedback_row("G60-0001", "SYNTHETIC: I want a hover mode and the seats are comfy.", "Seats",
                         "Likes", "Likes comfort"),
            feedback_row("G60-0002", "SYNTHETIC: Really love this car!", "no_class_found", country="GB", engine="ICE"),
        ]
        save(self.data / "G60_feedback_hackathon.xlsx", {"Feedback_Explorer": [FEEDBACK_HEADER] + self.feedback_rows})
        save(self.data / EXPORT.STUDY_FILE, {
            "CN_EU_2025": [
                [None, "Dataset country", None, None],
                [None, "China", "EU", None],
                ["Overall product satisfaction", "BMW 5 Series G68", "BMW 5 Series G60", "BMW 7 Series G70"],
                ["Mean", 8.5, 8.25, 9.0],
                ["Luggage capacity", None, None, None],
                ["Mean", "7.5", 7.25, 7.0],
            ],
            "US_2025": [["Cupholders", None, "BMW 5 Series G60", "BMW 7 Series G70 "],
                        ["Sample total", "% of column, sample base", 1, 1]]
                       + [[label, "% of column, sample base", 0.1, 0.1] for label in EXPORT.US_SCALE[:-1]]
                       + [[EXPORT.US_SCALE[-1], "% of column, sample base", 0.4, 0.4]],
        })
        header = ["market", "market_code", "volume_2024", "volume_2025", "volume_2030"]
        save(self.data / EXPORT.SALES_FILE, {
            "G60_G68": [header, ["Europe", "EU", 100, 110, 120], ["Rest of World", "RoW", 10, 11, 12]],
            "F70": [header, ["China", "CN", "=0*1", 0, 0]],
        })

    def export(self, *extra):
        argv = ["--data-dir", str(self.data), "--output", str(self.output), "--catalog", str(self.catalog),
                "--date", "20261010", *extra]
        return EXPORT.build(EXPORT.parse_args(argv))

    def records(self, topic):
        path = next(self.output.glob(f"luis-20261010-{topic}")) / "records.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()]

    def test_feedback_collapses_classification_rows_and_keeps_label_order(self):
        report = self.export("--datasets", "feedback")
        self.assertEqual(report["batches"][0]["classification_rows"], 3)
        first, second = self.records("bmw-feedback-g60")
        self.assertEqual(first["locator"]["rows"], [2, 3])
        self.assertEqual(first["source_fields"]["Source"], "Source A")
        self.assertEqual(first["subject_ids"], ["bmw:G60"])
        self.assertEqual(first["markets"], ["US"])
        labels = [(label["name"], label["value"]) for label in first["source_fields"]["original_labels"]]
        self.assertEqual(labels, [
            ("Engine Type", "BEVE"),
            ("Vfc level2 Name", "Synthetic hover mode"), ("Feedback Type", "Wants"),
            ("Vfc level3 Name", "Customer request: function"),
            ("Vfc level2 Name", "Seats"), ("Feedback Type", "Likes"), ("Vfc level3 Name", "Likes comfort"),
        ])
        self.assertEqual(second["markets"], ["GB"])

    def test_conflicting_feedback_id_is_reported_not_merged(self):
        self.feedback_rows.append(feedback_row("G60-0002", "SYNTHETIC: different text under the same ID."))
        save(self.data / "G60_feedback_hackathon.xlsx", {"Feedback_Explorer": [FEEDBACK_HEADER] + self.feedback_rows})
        report = self.export("--datasets", "feedback")
        self.assertEqual(report["batches"][0]["conflicting_ids"], [{"id": "G60-0002", "rows": [4, 5]}])
        self.assertEqual([r["dedup_key"] for r in self.records("bmw-feedback-g60")], ["bmw-feedback:G60:G60-0001"])
        notes = (self.output / "luis-20261010-bmw-feedback-g60" / "notes.md").read_text()
        self.assertIn("G60-0002", notes)

    def test_study_sheets_keep_cohorts_and_scales_apart(self):
        self.export("--datasets", "study")
        cn_eu = {(tuple(r["subject_ids"]), tuple(r["markets"]), r["metric"]["name"]): r for r in self.records("bmw-study-cn-eu-2025")}
        self.assertEqual(len(cn_eu), 6)
        g68 = cn_eu[(("bmw:G68",), ("CN",), "Overall product satisfaction")]
        self.assertEqual((g68["metric"]["statistic"], g68["metric"]["scale"], g68["locator"]["rows"]), ("mean", None, [3, 4]))
        self.assertEqual(cn_eu[(("bmw:G60",), ("EU",), "Luggage capacity")]["metric"]["value"], 7.25)
        self.assertIn((("bmw:G70",), ("EU",), "Luggage capacity"), cn_eu)
        us = self.records("bmw-study-us-2025")
        self.assertEqual(len(us), 2 * len(EXPORT.US_SCALE))
        names = {r["metric"]["name"] for r in us}
        self.assertIn("Cupholders | I Love It", names)
        self.assertFalse(any("Sample total" in name for name in names))
        self.assertTrue(all(r["metric"]["statistic"] == "proportion" and r["metric"]["sample_base"] is None for r in us))
        self.assertIn("BMW 7 Series G70", {label["value"] for r in us for label in r["source_fields"]["original_labels"]})

    def test_sales_keep_combined_model_and_unknown_formula_values(self):
        self.export("--datasets", "sales")
        records = {r["dedup_key"]: r for r in self.records("bmw-sales-volumes")}
        europe = records["bmw-sales:G60_G68:EU:2030"]
        self.assertEqual((europe["subject_ids"], europe["metric"]["statistic"]), (["bmw:G60_G68"], "forecast"))
        self.assertEqual(records["bmw-sales:G60_G68:EU:2024"]["metric"]["statistic"], "count")
        self.assertEqual(records["bmw-sales:G60_G68:RoW:2025"]["markets"], [])
        # A formula without a cached value is reported, never computed or invented.
        self.assertNotIn("bmw-sales:F70:CN:2024", records)
        notes = (self.output / "luis-20261010-bmw-sales-volumes" / "notes.md").read_text()
        self.assertIn("F70!C2", notes)

    def test_output_validates_and_reruns_keep_snapshot_ids(self):
        self.export()
        self.assertEqual(VALIDATOR.validate_batches(self.output)[:2], (4, 2 + 6 + 14 + 8))
        first = {r["record_id"] for topic in ("bmw-feedback-g60", "bmw-sales-volumes") for r in self.records(topic)}
        self.export()
        second = {r["record_id"] for topic in ("bmw-feedback-g60", "bmw-sales-volumes") for r in self.records(topic)}
        self.assertEqual(first, second)
        source = json.loads((self.output / "luis-20261010-bmw-feedback-g60" / "source.json").read_text())
        self.assertEqual((source["review_status"], source["export_permissions"]["external_llm"]), ("pending", None))

    def test_catalog_gains_missing_topics_once(self):
        before = json.loads(self.catalog.read_text())["features"]
        report = self.export("--datasets", "feedback")
        after = json.loads(self.catalog.read_text())["features"]
        self.assertEqual(after[:len(before)], before)
        self.assertEqual(report["catalog_added"], ["synthetic_hover_mode"])
        self.assertEqual(after[-1]["label"], "Synthetic hover mode")
        self.assertIn("no_class_found", report["catalog_skipped_topics"])
        self.assertEqual(self.export("--datasets", "feedback")["catalog_added"], [])

    def test_granting_a_permission_requires_a_note(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            EXPORT.parse_args(["--external-llm", "true"])


if __name__ == "__main__":
    unittest.main()
