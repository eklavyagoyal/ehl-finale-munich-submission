"""Build an offline, source-linked LLM packet and reviewed-claim frequency counts."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import NamedTemporaryFile
from uuid import uuid4

from validate_research import ROOT, json_file, load_batches

REQUEST_TYPES = {"new_request", "discontinued", "competitor_parity"}
TARGET_MODELS = ["bmw:F70", "bmw:G60", "bmw:G70"]


def source_exclusions(source, demo):
    reasons = []
    if demo:
        if not source["is_example"]:
            reasons.append("real_source_excluded_from_demo")
    else:
        if source["is_example"]:
            reasons.append("synthetic_example")
        if source["review_status"] != "accepted":
            reasons.append("source_not_accepted")
    if source["review_status"] == "rejected" and demo:
        reasons.append("source_rejected")
    if source["export_permissions"]["external_llm"] is not True:
        reasons.append("external_llm_permission_not_confirmed")
    return reasons


def latest_records(records, sources):
    """Deduplicate only stable identities within a source dataset namespace."""
    selected = {}
    for record in sorted(records.values(), key=lambda item: item["record_id"]):
        source = sources[record["source_id"]]
        key = (source["dataset_key"], record["dedup_key"])
        previous = selected.get(key)
        if previous is None:
            selected[key] = record
            continue
        current_time = datetime.fromisoformat(source["collected_at"].replace("Z", "+00:00"))
        previous_time = datetime.fromisoformat(sources[previous["source_id"]]["collected_at"].replace("Z", "+00:00"))
        if current_time == previous_time:
            current_content = {k: v for k, v in record.items() if k not in {"record_id", "source_id"}}
            previous_content = {k: v for k, v in previous.items() if k not in {"record_id", "source_id"}}
            if current_content != previous_content:
                raise ValueError("Conflicting snapshots of one observation have equal collection timestamps; review the batches")
        elif current_time > previous_time:
            selected[key] = record
    retained = {record["record_id"]: record for record in selected.values()}
    superseded = [
        {"record_id": record["record_id"], "retained_record_id": selected[(sources[record["source_id"]]["dataset_key"], record["dedup_key"])]["record_id"]}
        for record in sorted(records.values(), key=lambda item: item["record_id"])
        if record["record_id"] not in retained
    ]
    return retained, superseded


def feature_frequencies(records, claims, sources, feature_catalog):
    """Count parent feedback records once per feature, preserving source cohorts."""
    labels = {feature["feature_key"]: feature.get("label", feature["feature_key"]) for feature in feature_catalog["features"]}
    cohorts = defaultdict(set)
    source_ids = defaultdict(set)
    dates = defaultdict(list)
    record_cohorts = {}
    for record in records.values():
        if record["record_kind"] != "feedback":
            continue
        source = sources[record["source_id"]]
        sampling = source["sampling"]
        key = (source["dataset_key"], source["channel"], tuple(sorted(record["subject_ids"])), tuple(sorted(record["markets"])), sampling["method"], sampling["query"])
        cohorts[key].add(record["record_id"])
        source_ids[key].add(record["source_id"])
        if record["content_date"]:
            dates[key].append(record["content_date"])
        record_cohorts[record["record_id"]] = key

    feature_reviews, feature_types = defaultdict(set), defaultdict(lambda: defaultdict(set))
    cohort_reviews, cohort_types = defaultdict(set), defaultdict(lambda: defaultdict(set))
    reviewed_parents = set()
    for claim in claims.values():
        parent = claim["record_id"]
        if parent not in record_cohorts:
            continue
        reviewed_parents.add(parent)
        feature = claim["feature_key"]
        if feature is None:
            continue
        key = (record_cohorts[parent], feature)
        feature_reviews[feature].add(parent)
        feature_types[feature][claim["claim_type"]].add(parent)
        cohort_reviews[key].add(parent)
        cohort_types[key][claim["claim_type"]].add(parent)

    def counts(review_ids, types):
        requests = set().union(*(types.get(kind, set()) for kind in REQUEST_TYPES))
        return {
            "mention_review_count": len(review_ids),
            "request_review_count": len(requests),
            "review_counts_by_claim_type": {kind: len(parents) for kind, parents in sorted(types.items())},
            "record_ids": sorted(review_ids),
        }

    overall = [
        {"feature_key": feature, "feature_label": labels[feature], **counts(parents, feature_types[feature])}
        for feature, parents in feature_reviews.items()
    ]
    overall.sort(key=lambda item: (-item["mention_review_count"], item["feature_key"]))
    breakdown = []
    for (key, feature), parents in cohort_reviews.items():
        dataset, channel, subjects, markets, method, query = key
        denominator = len(cohorts[key])
        known_dates = dates[key]
        breakdown.append({
            "feature_key": feature, "dataset_key": dataset, "channel": channel,
            "subject_ids": list(subjects), "markets": list(markets),
            "collection_method": method, "query": query, "source_ids": sorted(source_ids[key]),
            "content_date_start": min(known_dates) if known_dates else None,
            "content_date_end": max(known_dates) if known_dates else None,
            "feedback_review_count": denominator,
            "reviews_with_reviewed_claims": len(cohorts[key] & reviewed_parents),
            "mention_share_of_collected_reviews": len(parents) / denominator,
            **counts(parents, cohort_types[(key, feature)]),
        })
    breakdown.sort(key=lambda item: (-item["mention_review_count"], item["feature_key"], json.dumps(item["source_ids"])))
    return {"by_feature": overall, "by_cohort": breakdown}, reviewed_parents


def git_value(*arguments):
    try:
        return subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("Unable to read bounded Git metadata for the context snapshot") from error


def build_context(batch_root, demo=False, run_id=None):
    data = load_batches(batch_root)
    exclusions, eligible_sources = [], {}
    namespaces = {}
    for source_id, source in sorted(data["sources"].items()):
        reasons = source_exclusions(source, demo)
        if reasons:
            exclusions.append({"source_id": source_id, "reasons": reasons})
            continue
        dataset = source["dataset_key"]
        if dataset in namespaces and namespaces[dataset] != source["channel"]:
            raise ValueError("One dataset namespace spans different channels; resolve source identity before export")
        namespaces[dataset] = source["channel"]
        eligible_sources[source_id] = source
    if not eligible_sources:
        raise ValueError("No eligible evidence: review source status, example flags, and external_llm permissions (or use --demo for fixtures)")

    eligible_records = {key: record for key, record in data["records"].items() if record["source_id"] in eligible_sources}
    records, superseded = latest_records(eligible_records, eligible_sources)
    sources = {key: eligible_sources[key] for key in sorted({record["source_id"] for record in records.values()})}
    claims, omitted_claims = {}, []
    for claim_id, claim in sorted(data["claims"].items()):
        if claim["record_id"] not in records:
            reason = "parent_not_retained"
        elif claim["review_status"] == "rejected":
            reason = "claim_rejected"
        elif claim["review_status"] != "accepted" and not demo:
            reason = "claim_not_accepted"
        else:
            claims[claim_id] = claim
            continue
        omitted_claims.append({"claim_id": claim_id, "reason": reason})

    frequency, reviewed_parents = feature_frequencies(records, claims, sources, data["catalogs"]["features"])
    fingerprints = data["fingerprints"]
    policy = json_file(ROOT / "research/decision-model.json", fingerprints)
    instructions = {}
    for label, relative in (("synthesis_prompt", "research/prompts/synthesize.md"), ("challenge_brief", "docs/challenge/brief.md")):
        path = ROOT / relative
        raw = path.read_bytes()
        fingerprints[path] = hashlib.sha256(raw).hexdigest()
        instructions[label] = raw.decode("utf-8")
    for relative in ("scripts/build_research_context.py", "scripts/validate_research.py"):
        path = ROOT / relative
        fingerprints[path] = hashlib.sha256(path.read_bytes()).hexdigest()

    def input_name(path):
        path = path.resolve()
        if path.is_relative_to(ROOT.resolve()):
            return "repo:" + path.relative_to(ROOT.resolve()).as_posix()
        return "batch:" + path.relative_to(batch_root.resolve()).as_posix()

    feedback = [record for record in records.values() if record["record_kind"] == "feedback"]
    scope_counts = Counter(
        (tuple(sorted(record["subject_ids"])), tuple(sorted(record["markets"])), record["record_kind"], sources[record["source_id"]]["channel"])
        for record in records.values()
    )
    return {
        "run_manifest": {
            "run_id": run_id or uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(), "is_demo": demo,
            "git_commit": git_value("rev-parse", "HEAD"),
            "working_tree_dirty": bool(git_value("status", "--porcelain", "--untracked-files=all")),
            "schema_version": "1.0", "model": None,
            "input_sha256": {input_name(path): digest for path, digest in sorted(fingerprints.items())},
        },
        "scope": {"target_model_ids": TARGET_MODELS, "planning_horizon": "successor_vehicle_3_to_5_years", "market_filter": None},
        "coverage": {
            "input_source_count": len(data["sources"]), "input_record_count": len(data["records"]),
            "exported_source_count": len(sources), "exported_record_count": len(records), "exported_claim_count": len(claims),
            "records_by_kind": dict(sorted(Counter(record["record_kind"] for record in records.values()).items())),
            "records_by_channel": dict(sorted(Counter(sources[record["source_id"]]["channel"] for record in records.values()).items())),
            "record_counts_by_scope": [
                {"subject_ids": list(subjects), "markets": list(markets), "record_kind": kind, "channel": channel, "record_count": count}
                for (subjects, markets, kind, channel), count in sorted(scope_counts.items())
            ],
            "records_with_direct_target_subject": {
                model: sum(model in record["subject_ids"] for record in records.values()) for model in TARGET_MODELS
            },
            "feedback_review_count": len(feedback), "feedback_with_reviewed_claims": len(reviewed_parents),
            "unknown_subject_record_count": sum(not record["subject_ids"] for record in records.values()),
            "unknown_market_record_count": sum(not record["markets"] for record in records.values()),
            "unmapped_feature_claim_count": sum(claim["feature_key"] is None for claim in claims.values()),
            "excluded_sources": exclusions, "superseded_records": superseded, "omitted_claims": omitted_claims,
            "frequency_basis": "accepted_claims_on_retained_feedback_records; demo also permits pending synthetic claims",
            "limitations": [
                "Counts describe collected reviews, not unique people or customer prevalence.",
                "Reviews with claims may not have complete feature extraction; missing mentions are not established absence.",
                "Claim-type counts can overlap within a feature; do not sum them as distinct reviews.",
                "Combined, brand-wide, and unresolved subjects remain unallocated to individual target models.",
                "Cohorts pool retained observations with matching dataset/channel/subjects/markets/method/query across collection windows.",
                "Comparison sidecars and narrative notes require separate review and are not automatically ingested.",
            ],
        },
        "instructions": instructions, "catalogs": data["catalogs"],
        "sources": [sources[key] for key in sorted(sources)],
        "records": [records[key] for key in sorted(records)],
        "claims": [claims[key] for key in sorted(claims)],
        "feature_frequency": frequency,
        "comparison_context": {"status": "pending_reviewed_matches", "matches": []},
        "decision_policy": policy,
    }


def write_context(packet, output, max_bytes=None):
    output = output.resolve()
    allowed = ROOT.resolve() / "outputs/research"
    if not output.is_relative_to(allowed):
        raise ValueError("Context output must be inside this repository's ignored outputs/research directory")
    encoded = (json.dumps(packet, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    if max_bytes is not None and len(encoded) > max_bytes:
        raise ValueError("Context exceeds --max-bytes; reduce the input scope explicitly rather than truncating")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
        # Publish a complete file atomically without replacing an earlier run.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return len(encoded)


def positive_integer(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_root", type=Path)
    parser.add_argument("--demo", action="store_true", help="Use only synthetic fixtures, allowing their pending review status")
    parser.add_argument("--output", type=Path, help="New output file under outputs/research; existing files are never replaced")
    parser.add_argument("--max-bytes", type=positive_integer, help="Optional file-size ceiling; this is not a model token budget")
    args = parser.parse_args()
    try:
        packet = build_context(args.batch_root, demo=args.demo)
        output = args.output or ROOT / "outputs/research" / packet["run_manifest"]["run_id"] / "context.json"
        size = write_context(packet, output, args.max_bytes)
    except (OSError, ValueError) as error:
        print(f"Context export failed: {error}", file=sys.stderr)
        return 1
    print(f"Built {'synthetic demo' if args.demo else 'reviewed evidence'} context: {output}")
    print(f"{len(packet['records'])} records; {len(packet['claims'])} claims; {size} UTF-8 bytes. No LLM request was made.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
