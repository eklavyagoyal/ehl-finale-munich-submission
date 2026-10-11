"""Validate research/batches/competitors with the team's validator, without merging their branch.

Copies schema, validator and catalogs from a git ref (default origin/feat/research-handoff) into a temporary
directory, appends competitors/contract/catalog_additions.json to the catalogs, and runs
scripts/validate_research.py on our batches.

Usage: .venv/bin/python competitors/tools/validate_contract.py [--ref origin/feat/research-handoff]
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def show(ref: str, path: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"], check=True, capture_output=True,
                          text=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/feat/research-handoff")
    ap.add_argument("--batches", default=str(REPO / "research" / "batches" / "competitors"))
    args = ap.parse_args()

    additions = json.loads((REPO / "competitors" / "contract" / "catalog_additions.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "research" / "catalog").mkdir(parents=True)
        (root / "scripts").mkdir()
        (root / "research" / "schema.json").write_text(show(args.ref, "research/schema.json"))
        (root / "scripts" / "validate_research.py").write_text(show(args.ref, "scripts/validate_research.py"))
        for name, key, id_key in (("entities", "entities", "entity_id"), ("features", "features", "feature_key")):
            catalog = json.loads(show(args.ref, f"research/catalog/{name}.json"))
            known = {e[id_key] for e in catalog[key]}
            clash = [e[id_key] for e in additions[key] if e[id_key] in known]
            if clash:
                print(f"note: {name} already in team catalog, not re-added: {clash}")
            catalog[key] += [e for e in additions[key] if e[id_key] not in known]
            (root / "research" / "catalog" / f"{name}.json").write_text(json.dumps(catalog, indent=2))
        result = subprocess.run([sys.executable, str(root / "scripts" / "validate_research.py"), args.batches],
                                capture_output=True, text=True)
        print((result.stdout + result.stderr).strip())
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
