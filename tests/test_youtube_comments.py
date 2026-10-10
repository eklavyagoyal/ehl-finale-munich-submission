"""Offline tests for the YouTube scraper: the API is replaced by canned responses.

Run from the repo root: .venv/bin/python -m unittest discover tests
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pyarrow.parquet as pq
import yaml

from scrapers import warehouse, youtube_comments as yt

CONFIG = yaml.safe_load(
    (Path(__file__).resolve().parent.parent / "scrapers/configs/bmw_5_series_youtube.yaml").read_text())


def comment(cid, text, when="2026-09-01T10:00:00Z", likes=0):
    return {"id": cid, "snippet": {"textDisplay": text, "publishedAt": when, "likeCount": likes}}


def thread(cid, text, replies=()):
    return {"snippet": {"topLevelComment": comment(cid, text), "totalReplyCount": len(replies)},
            "replies": {"comments": list(replies)}}


class FakeYouTube:
    """Answers youtube_get() calls from a small fixture and counts calls per endpoint."""

    def __init__(self):
        self.calls = []
        self.pages = {
            "vidA": [{"items": [thread("c1", "Rear seat space is too small", [comment("r1", "agree")]),
                                thread("c2", "Love the i5 range")], "nextPageToken": "p2"},
                     {"items": [thread("c3", "Too many menus in iDrive")]}],
        }

    def __call__(self, endpoint, params, attempts=4):
        self.calls.append(endpoint)
        if endpoint == "search":
            return {"items": [
                {"id": {"videoId": "vidA"}, "snippet": {"title": "BMW 5er G60 im Test"}},
                {"id": {"videoId": "vidB"}, "snippet": {"title": "BMW X5 review"}},       # wrong model
                {"id": {"videoId": "vidC"}, "snippet": {"title": "BMW i5 Fahrbericht"}},  # comments off
                {"id": {"videoId": "vidD"}, "snippet": {"title": "BMW 540i (G30) review"}},  # old generation
                {"id": {"videoId": "vidE"}, "snippet": {"title": "BMW 5 G60 test PL"}},     # wrong language
            ]}
        if endpoint == "videos":
            return {"items": [
                {"id": vid, "snippet": {"title": t, "channelTitle": "ch", "publishedAt": "2024-01-01T00:00:00Z",
                                        "defaultAudioLanguage": lang},
                 "statistics": {"viewCount": "1000", "commentCount": "3"}}
                for vid, t, lang in [("vidA", "BMW 5er G60 im Test", "de-DE"), ("vidC", "BMW i5 Fahrbericht", None),
                                     ("vidE", "BMW 5 G60 test PL", "pl")]
                if vid in params["id"].split(",")]}
        if endpoint == "commentThreads":
            if params["videoId"] == "vidC":
                raise yt.CommentsUnavailable("commentsDisabled")
            page = 1 if params.get("pageToken") == "p2" else 0
            return self.pages[params["videoId"]][page]
        raise AssertionError(endpoint)


class YouTubeScraperTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(warehouse, "WAREHOUSE_DIR", Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.fake = FakeYouTube()
        patcher = mock.patch.object(yt, "youtube_get", self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.config_path = Path(self.tmp.name) / "config.yaml"
        self.config_path.write_text(yaml.safe_dump(CONFIG))

    def table(self, name):
        return pq.read_table(Path(self.tmp.name) / f"{name}.parquet").to_pandas()

    def test_scrape_filters_paginates_and_skips_disabled(self):
        yt.scrape(self.config_path, markets=["de"], workers=1)
        facts = self.table("fact_video_comment")
        self.assertEqual(sorted(facts["comment_id"]),
                         ["youtube:c1", "youtube:c2", "youtube:c3", "youtube:r1"])
        reply = facts[facts["comment_id"] == "youtube:r1"].iloc[0]
        self.assertEqual(reply["parent_comment_id"], "youtube:c1")
        self.assertEqual(facts[facts["comment_id"] == "youtube:c1"].iloc[0]["reply_count"], 1)
        self.assertEqual(set(facts["source"]), {"youtube"})

        videos = self.table("dim_video")
        # X5 and G30 filtered by title, Polish video by language, vidC had no comments.
        self.assertEqual(set(videos["youtube_video_id"]), {"vidA"})
        self.assertEqual(videos["video_language"].tolist(), ["de-DE"])
        self.assertNotIn("vidE", [c for c in self.fake.calls if c == "commentThreads"])
        self.assertEqual(self.table("dim_market")["market_code"].tolist(), ["DE"])
        self.assertEqual(self.table("dim_vehicle_model")["vehicle_code"].tolist(), ["G60"])

    def test_rerun_is_incremental_and_keys_are_stable(self):
        yt.scrape(self.config_path, markets=["de"], workers=1)
        first = self.table("fact_video_comment").sort_values("comment_id")
        self.fake.calls.clear()
        yt.scrape(self.config_path, markets=["de"], workers=1)
        second = self.table("fact_video_comment").sort_values("comment_id")

        self.assertEqual(len(first), len(second))
        self.assertEqual(first["video_id"].tolist(), second["video_id"].tolist())
        # Page 1 of vidA holds only known comments, so page 2 is not requested again.
        self.assertEqual(self.fake.calls.count("commentThreads"), 2)  # vidA page 1 + vidC

    def test_date_from_drops_old_comments_and_stops_paging(self):
        # Page 1 ends with a thread from 2023: it is dropped and page 2 is never requested.
        self.fake.pages["vidA"][0]["items"].append(
            {"snippet": {"topLevelComment": comment("old", "launch day", when="2023-06-01T10:00:00Z"),
                         "totalReplyCount": 0}})
        yt.scrape(self.config_path, markets=["de"], workers=1)
        ids = set(self.table("fact_video_comment")["comment_id"])
        self.assertNotIn("youtube:old", ids)
        self.assertNotIn("youtube:c3", ids)  # on page 2, past the cutoff
        self.assertEqual(self.fake.calls.count("commentThreads"), 2)  # vidA page 1 + vidC

    def test_quota_exceeded_keeps_collected_data(self):
        original = self.fake.__call__

        def quota_on_comments(endpoint, params, attempts=4):
            if endpoint == "commentThreads":
                raise yt.QuotaExceeded("quota")
            return original(endpoint, params)

        with mock.patch.object(yt, "youtube_get", quota_on_comments):
            yt.scrape(self.config_path, markets=["de"], workers=1)  # must not raise


if __name__ == "__main__":
    unittest.main()
