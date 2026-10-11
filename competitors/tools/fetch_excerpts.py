"""Find exact source excerpts for core equipment features (F03, F04, F08, F10, F13, F16).

For each equipment record of those features with a known availability, fetch the cited page once (plain GET, no
login, no workaround; PDFs via pdftotext), normalise whitespace and look for a sentence window that contains the
feature keyword and, where the record value has a kW figure, that number. Candidates go to
competitors/contract/excerpt_candidates.json for review; accepted ones (see --accept) to excerpts.json, which
export_contract.py appends to text_original.

Usage:
  .venv/bin/python competitors/tools/fetch_excerpts.py              # fetch + write candidates
  .venv/bin/python competitors/tools/fetch_excerpts.py --accept ID,ID,...   # promote reviewed candidates
"""

import argparse
import html
import json
import re
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contract"
CANDIDATES = ROOT.parent / "outputs" / "competitors" / "excerpt_candidates.json"  # gitignored: raw page chunks
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) research-script (BMW hackathon, single request per page)"

KEYWORDS = {
    "F03_physical_climate_controls": r"climat|klima|空调|hvac|temperature",
    "F04_voice_assistant": r"voice|sprach|语音|assistant|assistent|chatgpt|deepseek|gemini|alexa|nomi|hey ",
    "F08_hands_free_highway": r"super cruise|highway assist|hands[- ]free|hands-off|autobahnassist|autopilot|"
                              r"noa|nop|领航|智驾|ads|qiankun|乾崑|blue ?cruise|distronic|lane[- ]?change",
    "F10_ventilated_front_seats": r"ventilat|belüft|lüftung|通风|cooled seat",
    "F13_air_suspension": r"air suspension|luftfeder|airmatic|空气悬架|air spring",
    "F16_dc_charging": r"kw|charg|lade|充电|快充",
}


def fetch_text(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,de;q=0.8,zh;q=0.6"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "")
    except Exception as e:
        print(f"  ! {url}: {e}")
        return None
    if url.lower().endswith(".pdf") or "pdf" in ctype:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(body)
            f.flush()
            out = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True)
            text = out.stdout
    else:
        raw = body.decode("utf-8", errors="replace")
        raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
        text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))
    return re.sub(r"\s+", " ", text).strip()


def windows(text: str, rx: str, number: str | None) -> list[str]:
    out = []
    for m in re.finditer(rx, text, re.I):
        start, end = max(0, m.start() - 160), min(len(text), m.end() + 160)
        chunk = text[start:end]
        if number and number not in chunk:
            continue
        cjk = len(re.findall(r"[一-鿿]", chunk)) > 20
        if cjk:
            centre = m.start() - start
            excerpt = chunk[max(0, centre - 30): centre + 40]
        else:
            words = chunk.split(" ")
            # keep the words around the match, at most 24
            pos = len(text[start:m.start()].split(" ")) - 1
            excerpt = " ".join(words[max(1, pos - 11): pos + 13])
        excerpt = excerpt.strip(" ,;:-")
        if excerpt and excerpt in text and excerpt not in out:
            out.append(excerpt)
        if len(out) >= 3:
            break
    return out


def trim(excerpt: str, feature: str, value: str | None) -> str:
    """Shorten an excerpt to <= 15 words (or 40 CJK characters) around the evidence; stays an exact substring."""
    kw = re.search(r"(\d{2,4})\s?kW", value or "") if feature == "F16_dc_charging" else None
    anchor = re.search(re.escape(kw.group(1)) if kw and kw.group(1) in excerpt else KEYWORDS[feature], excerpt, re.I)
    centre = anchor.start() if anchor else len(excerpt) // 2
    if len(re.findall(r"[\u4e00-\u9fff]", excerpt)) > 20:
        return excerpt if len(excerpt) <= 40 else excerpt[max(0, centre - 15): centre + 25].strip()
    words = excerpt.split(" ")
    if len(words) <= 15:
        return excerpt
    pos = len(excerpt[:centre].split(" ")) - 1
    start = min(max(0, pos - 6), len(words) - 15)
    return " ".join(words[start:start + 15])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--accept", help="comma-separated candidate ids (record_id#n) to promote")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    cand_path, exc_path = CANDIDATES, OUT / "excerpts.json"
    cand_path.parent.mkdir(parents=True, exist_ok=True)

    if args.accept:
        cands = json.loads(cand_path.read_text())["candidates"]
        accepted = json.loads(exc_path.read_text())["excerpts"] if exc_path.exists() else {}
        for cid in args.accept.split(","):
            rid, n = cid.strip().rsplit("#", 1)
            c = cands[rid]
            accepted[rid] = {"url": c["url"], "fetched_at": c["fetched_at"],
                             "excerpt": trim(c["excerpts"][int(n)], c["feature"], c.get("record_value")),
                             "feature": c["feature"], "reviewed": "keyword match checked against record by collector"}
        exc_path.write_text(json.dumps({"description": "Exact excerpts (whitespace-normalised page text) accepted after "
                                        "review; used by export_contract.py.", "excerpts": accepted},
                                       ensure_ascii=False, indent=2) + "\n")
        print(f"{len(accepted)} accepted excerpts")
        return

    recs = [json.loads(l) for l in (ROOT / "findings.jsonl").read_text().splitlines() if l.strip()]
    sel = [r for r in recs if r["kind"] == "equipment" and r["feature"] in KEYWORDS
           and r["availability"] != "unknown" and r["url"].startswith("http")]
    pages, cands = {}, {}
    for r in sel:
        if r["url"] not in pages:
            pages[r["url"]] = (fetch_text(r["url"]), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
            time.sleep(0.5)
        text, fetched = pages[r["url"]]
        if not text:
            continue
        kw = re.search(r"(\d{2,4})\s?kW", r.get("value") or "")
        found = windows(text, KEYWORDS[r["feature"]], kw.group(1) if (kw and r["feature"] == "F16_dc_charging") else None)
        if found:
            cands[r["record_id"]] = {"url": r["url"], "fetched_at": fetched, "feature": r["feature"],
                                     "vehicle": f"{r['brand']} {r['model']} ({r['market']})",
                                     "record_value": r.get("value"), "availability": r["availability"],
                                     "excerpts": found}
    cand_path.write_text(json.dumps({"description": "Keyword-matched excerpt candidates, to be reviewed.",
                                     "candidates": cands}, ensure_ascii=False, indent=2) + "\n")
    ok = sum(1 for t, _ in pages.values() if t)
    print(f"{len(sel)} records, {len(pages)} pages ({ok} fetched), {len(cands)} records with candidates")


if __name__ == "__main__":
    main()
