"""Load and validate research contract v1 batches.

Mirrors `scripts/validate_research.py` from the research branch (same checks, same error
style, no source content in messages), but takes explicit paths so the backend can read a
research checkout that lives anywhere.
"""

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


@dataclass
class ContractPaths:
    research_root: Path

    @property
    def schema(self) -> Path:
        return self.research_root / "schema.json"

    @property
    def entities(self) -> Path:
        return self.research_root / "catalog" / "entities.json"

    @property
    def features(self) -> Path:
        return self.research_root / "catalog" / "features.json"

    @property
    def decision_model(self) -> Path:
        return self.research_root / "decision-model.json"


@dataclass
class LoadedBatches:
    sources: dict[str, dict]
    records: dict[str, dict]
    claims: dict[str, dict]
    catalogs: dict[str, dict]
    fingerprints: dict[str, str] = field(default_factory=dict)


def _reject_constant(value):
    raise ValueError("Non-finite numbers are not valid JSON")


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Number exceeds finite float range")
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def parse_json(text: str, location) -> object:
    try:
        return json.loads(
            text, parse_constant=_reject_constant, parse_float=_finite_float, object_pairs_hook=_unique_object
        )
    except ValueError as error:
        raise ValueError(f"{location}: invalid JSON") from error


def json_file(path: Path, fingerprints: dict | None = None):
    raw = path.read_bytes()
    document = parse_json(raw.decode("utf-8"), path)
    if fingerprints is not None:
        fingerprints[str(path)] = hashlib.sha256(raw).hexdigest()
    return document


def json_lines(path: Path, fingerprints: dict | None = None):
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
        fingerprints[str(path)] = digest.hexdigest()


def _catalog_ids(document: dict, path: Path, entries_key: str, id_key: str) -> set[str]:
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


def load_batches(batch_root: Path, paths: ContractPaths) -> LoadedBatches:
    """Validate every batch under `batch_root` against the contract and return the documents."""
    fingerprints: dict[str, str] = {}
    schema = json_file(paths.schema, fingerprints)
    Draft202012Validator.check_schema(schema)
    checker = FormatChecker()
    validators = {
        kind: Draft202012Validator(
            {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": f"#/$defs/{kind}"},
            format_checker=checker,
        )
        for kind in ("source", "record", "claim")
    }
    catalogs = {
        "entities": json_file(paths.entities, fingerprints),
        "features": json_file(paths.features, fingerprints),
    }
    entity_ids = _catalog_ids(catalogs["entities"], paths.entities, "entities", "entity_id")
    feature_keys = _catalog_ids(catalogs["features"], paths.features, "features", "feature_key")

    def check(document, kind, location):
        errors = list(validators[kind].iter_errors(document))
        if errors:
            error = errors[0]
            where = ".".join(str(item) for item in error.absolute_path) or "<root>"
            raise ValueError(f"{location}: {kind} field {where} violates {error.validator}")

    manifests = sorted(batch_root.rglob("source.json"))
    if not manifests:
        raise ValueError(f"{batch_root}: no source.json batches found")
    expected = {path.parent / name for path in manifests for name in ("records.jsonl", "claims.jsonl")}
    if set(batch_root.rglob("*.jsonl")) - expected:
        raise ValueError(f"{batch_root}: JSONL file outside a recognized batch")

    sources: dict[str, dict] = {}
    records: dict[str, dict] = {}
    pending_claims: list[tuple[dict, str, str]] = []
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
            if metric and metric["scale"] and not metric["scale"]["min"] <= metric["value"] <= metric["scale"]["max"]:
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
                pending_claims.append((claim, location, source_id))

    claims: dict[str, dict] = {}
    for claim, location, source_id in pending_claims:
        if claim["claim_id"] in claims:
            raise ValueError(f"{location}: duplicate claim_id")
        record = records.get(claim["record_id"])
        if record is None or record["source_id"] != source_id:
            raise ValueError(f"{location}: claim references a missing record or different batch")
        if claim["feature_key"] is not None and claim["feature_key"] not in feature_keys:
            raise ValueError(f"{location}: unknown claim feature_key")
        original = record["text_original"] or ""
        if any(quote not in original for quote in claim["quotes"]):
            raise ValueError(f"{location}: quote is not an exact substring of original evidence")
        claims[claim["claim_id"]] = claim
    return LoadedBatches(sources, records, claims, catalogs, fingerprints)
