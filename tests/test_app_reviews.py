"""Offline tests for the app review scraper's date window."""

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

from scrapers import app_reviews, warehouse


def apple_entry(review_id, when):
    return {"id": {"label": review_id}, "updated": {"label": when}, "title": {"label": "t"},
            "content": {"label": "text"}, "im:rating": {"label": "4"}, "im:version": {"label": "1.0"}}


class AppReviewsDateFromTest(unittest.TestCase):
    def test_apple_drops_old_reviews_and_stops_paging(self):
        pages = {1: [apple_entry("new", "2026-09-01T10:00:00-07:00"), apple_entry("old", "2023-12-31T10:00:00-07:00")],
                 2: [apple_entry("never", "2023-01-01T10:00:00-07:00")]}
        with mock.patch.object(app_reviews, "apple_page", side_effect=lambda a, m, page: pages.get(page, [])) as page:
            got = app_reviews.apple_reviews("1", "de", 500, set(), date(2024, 1, 1))
        self.assertEqual([r["review_id"] for r in got], ["app_store:new"])
        self.assertEqual(page.call_count, 1)

    def test_google_drops_old_reviews_and_stops_paging(self):
        batch = [{"reviewId": "new", "at": datetime(2026, 9, 1), "content": "x", "score": 5, "appVersion": "1"},
                 {"reviewId": "old", "at": datetime(2023, 5, 1), "content": "y", "score": 1, "appVersion": "1"}]
        with mock.patch.object(app_reviews, "gp_reviews", return_value=(batch, "next-token")) as call:
            got = app_reviews.google_reviews("pkg", "de", "de", 2000, set(), date(2024, 1, 1))
        self.assertEqual([r["review_id"] for r in got], ["google_play:new"])
        self.assertEqual(call.call_count, 1)

    def test_scrape_removes_stored_reviews_before_date_from(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(warehouse, "WAREHOUSE_DIR", Path(tmp)):
            old = {"store": "app_store", "store_app_id": "1", "market": "de", "review_id": "app_store:old",
                   "datetime": datetime(2023, 1, 1, tzinfo=timezone.utc), "content": "old", "rating": 3,
                   "app_version": None}
            for name, rows in warehouse.build_tables([old], []).items():
                warehouse.upsert(name, rows)
            config = Path(tmp) / "c.yaml"
            config.write_text(yaml.safe_dump({"apps": [{"store": "app_store", "app_id": "1", "markets": ["de"]}],
                                              "scrape": {"date_from": date(2024, 1, 1)}}))
            with mock.patch.object(app_reviews, "apple_app_info", return_value={"app_name": None}), \
                    mock.patch.object(app_reviews, "apple_reviews", return_value=[]):
                app_reviews.scrape(config, workers=1)
            self.assertEqual(len(warehouse.read_table("fact_review")), 0)


if __name__ == "__main__":
    unittest.main()
