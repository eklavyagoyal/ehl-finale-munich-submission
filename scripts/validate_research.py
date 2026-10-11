"""Validate research batches, record identity, and claim references."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def reject_constant(value):
    raise ValueError("Non-finite numbers are not valid JSON")


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Number exceeds finite float range")
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def parse_json(text, location):
    try:
        return json.loads(
            text, parse_constant=reject_constant, parse_float=finite_float,
            object_pairs_hook=unique_object,
        )
    except ValueError as error:
        # Do not print source content or offending field values.
        raise ValueError(f"{location}: invalid JSON") from error


def json_file(path, fingerprints=None):
    raw = path.read_bytes()
    document = parse_json(raw.decode("utf-8"), path)
    if fingerprints is not None:
        fingerprints[path] = hashlib.sha256(raw).hexdigest()
    return document


def json_lines(path, fingerprints=None):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for number, raw in enumerate(stream, 1):
            digest.update(raw)
            line = raw.decode("utf-8")
            location = f"{path}:{number}"
            if not line.strip():
                raise ValueError(f"{location}: blank JSONL line")
            yield parse_json(line, location), location
    if fingerprints is not None:
        fingerprints[path] = digest.hexdigest()


def catalog_ids(path, entries_key, id_key, document=None):
    if document is None:
        document = json_file(path)
    if not isinstance(document, dict) or not isinstance(document.get(entries_key), list):
        raise ValueError(f"{path}: catalog must contain an {entries_key} array")
    identifiers = set()
    for index, entry in enumerate(document[entries_key]):
        identifier = entry.get(id_key) if isinstance(entry, dict) else None
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"{path}: entry {index} requires a nonempty {id_key}")
        if identifier in identifiers:
            raise ValueError(f"{path}: duplicate {id_key}")
        identifiers.add(identifier)
    return identifiers


def load_batches(batch_root):
    """Return validated documents and hashes of the exact bytes parsed."""
    fingerprints = {}
    schema = json_file(ROOT / "research/schema.json", fingerprints)
    Draft202012Validator.check_schema(schema)
    checker = FormatChecker()
    validators = {
        kind: Draft202012Validator(
            {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": f"#/$defs/{kind}"},
            format_checker=checker,
        )
        for kind in ("source", "record", "claim")
    }
    catalogs = {}
    for name, id_key in (("entities", "entity_id"), ("features", "feature_key")):
        path = ROOT / f"research/catalog/{name}.json"
        catalogs[name] = json_file(path, fingerprints)
    entity_ids = catalog_ids(ROOT / "research/catalog/entities.json", "entities", "entity_id", catalogs["entities"])
    feature_keys = catalog_ids(ROOT / "research/catalog/features.json", "features", "feature_key", catalogs["features"])

    def check(document, kind, location):
        errors = list(validators[kind].iter_errors(document))
        if errors:
            error = errors[0]
            field = ".".join(str(item) for item in error.absolute_path) or "<root>"
            raise ValueError(f"{location}: {kind} field {field} violates {error.validator}")

    manifests = sorted(batch_root.rglob("source.json"))
    if not manifests:
        raise ValueError(f"{batch_root}: no source.json batches found")
    expected_files = {path.parent / name for path in manifests for name in ("records.jsonl", "claims.jsonl")}
    actual_files = set(batch_root.rglob("*.jsonl"))
    if actual_files - expected_files:
        raise ValueError(f"{batch_root}: JSONL file outside a recognized batch")
    sources, records, claims = {}, {}, []
    for path in manifests:
        source = json_file(path, fingerprints)
        check(source, "source", path)
        source_id = source["source_id"]
        if source_id in sources:
            raise ValueError(f"{path}: duplicate source_id")
        if source["is_example"] != (source["provenance"]["origin"] == "synthetic"):
            raise ValueError(f"{path}: is_example and synthetic origin disagree")
        sampling = source["sampling"]
        if sampling["date_start"] and sampling["date_end"] and sampling["date_start"] > sampling["date_end"]:
            raise ValueError(f"{path}: sampling date range is reversed")
        sources[source_id] = source
        count, dedup_keys = 0, set()
        for record, location in json_lines(path.parent / "records.jsonl", fingerprints):
            check(record, "record", location)
            if record["source_id"] != source_id:
                raise ValueError(f"{location}: record belongs to a different source")
            if record["record_id"] in records:
                raise ValueError(f"{location}: duplicate record_id")
            if record["dedup_key"] in dedup_keys:
                raise ValueError(f"{location}: duplicate observation within batch")
            if set(record["subject_ids"]) - entity_ids:
                raise ValueError(f"{location}: unknown subject_id; update entity catalog")
            metric = record["metric"]
            if metric and metric["scale"]:
                scale = metric["scale"]
                if not scale["min"] <= metric["value"] <= scale["max"]:
                    raise ValueError(f"{location}: metric outside scale or reversed scale")
            availability = record["availability"]
            if availability and availability["feature_key"] not in feature_keys:
                raise ValueError(f"{location}: unknown availability feature_key")
            records[record["record_id"]] = record
            dedup_keys.add(record["dedup_key"])
            count += 1
        if count != source["normalized_record_count"]:
            raise ValueError(f"{path}: normalized_record_count does not match records.jsonl")
        claim_path = path.parent / "claims.jsonl"
        if claim_path.exists():
            for claim, location in json_lines(claim_path, fingerprints):
                check(claim, "claim", location)
                claims.append((claim, location, source_id))

    claim_ids = set()
    for claim, location, source_id in claims:
        if claim["claim_id"] in claim_ids:
            raise ValueError(f"{location}: duplicate claim_id")
        record = records.get(claim["record_id"])
        if record is None or record["source_id"] != source_id:
            raise ValueError(f"{location}: claim references a missing record or different batch")
        if claim["feature_key"] is not None and claim["feature_key"] not in feature_keys:
            raise ValueError(f"{location}: unknown claim feature_key")
        original = record["text_original"] or ""
        if any(quote not in original for quote in claim["quotes"]):
            raise ValueError(f"{location}: quote is not an exact substring of original evidence")
        claim_ids.add(claim["claim_id"])
    return {
        "sources": sources,
        "records": records,
        "claims": {claim["claim_id"]: claim for claim, _, _ in claims},
        "catalogs": catalogs,
        "fingerprints": fingerprints,
    }


def validate_batches(batch_root):
    documents = load_batches(batch_root)
    return tuple(len(documents[kind]) for kind in ("sources", "records", "claims"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_root", type=Path)
    args = parser.parse_args()
    try:
        sources, records, claims = validate_batches(args.batch_root)
    except (OSError, ValueError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 1
    print(f"Validated {sources} batches, {records} records, {claims} claims (structure and references only).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
