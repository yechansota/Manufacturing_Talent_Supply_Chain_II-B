"""Freeze the pre-registration, or verify that it is still frozen.

    python scripts/freeze.py            # freeze (only if all pre-analysis checks passed)
    python scripts/freeze.py --verify   # exit 1 if prereg.yaml or any raw file changed

Freezing:
  1. Confirms the pre-analysis checks passed (audit stop rule, OEWS frame
     validation, EP crosswalk check — their output files must exist and pass).
  2. Sets meta.status = "frozen" and meta.frozen_at_utc in config/prereg.yaml
     (text edit; comments are preserved).
  3. Writes outputs/freeze_record.md with SHA-256 of prereg.yaml, every raw file
     (from data/raw/MANIFEST.csv) and every audit/validation output.
After freezing, any change to prereg.yaml must be logged in outputs/deviation_log.md
before the affected analysis is run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "config" / "prereg.yaml"
RECORD = ROOT / "outputs" / "freeze_record.md"
MANIFEST = ROOT / "data" / "raw" / "MANIFEST.csv"
CHECK_FILES = [
    ROOT / "outputs" / "audit" / "audit_stop_rule.csv",
    ROOT / "outputs" / "audit" / "audit_crosswalk.csv",
    ROOT / "outputs" / "validation" / "oews_frame_validation.csv",
    ROOT / "outputs" / "validation" / "ep_crosswalk_check.csv",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def preconditions() -> list[str]:
    problems = [f"missing {p.relative_to(ROOT)} (run the pipeline first)" for p in CHECK_FILES if not p.exists()]
    if problems:
        return problems
    if not MANIFEST.exists():
        problems.append("missing data/raw/MANIFEST.csv (run scripts/check_downloads.py)")
    for row in read_csv(CHECK_FILES[0]):
        if row["decision"] == "CHECK: no flags":
            problems.append(f"stop rule undecided for domain {row['domain']}")
    for row in read_csv(CHECK_FILES[1]):
        if row["mapping_type"] == "primary" and row["found_any_domain"] != "True":
            problems.append(f"unresolved O*NET code {row['onet_code']}")
    for row in read_csv(CHECK_FILES[2]):
        if row["role"] in {"target_core", "feeder_core"} and row["rule_pass"] != "True":
            problems.append(f"{row['soc6']} fails its selection rule")
    for row in read_csv(CHECK_FILES[3]):
        if row["status"] != "OK":
            problems.append(f"crosswalk check failed for {row['soc6']}")
    return problems


def freeze() -> int:
    problems = preconditions()
    if problems:
        print("NOT FROZEN — pre-analysis checks incomplete:\n  - " + "\n  - ".join(problems))
        return 1
    text = PREREG.read_text(encoding="utf-8")
    if re.search(r'^\s*status:\s*"frozen"', text, flags=re.M):
        print("Already frozen; use --verify.")
        return 1
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text, n1 = re.subn(r'^(\s*status:\s*)"draft"', r'\1"frozen"', text, count=1, flags=re.M)
    text, n2 = re.subn(r'^(\s*frozen_at_utc:\s*)null', rf'\1"{ts}"', text, count=1, flags=re.M)
    if n1 != 1 or n2 != 1:
        print("Could not locate meta.status / meta.frozen_at_utc in prereg.yaml")
        return 1
    PREREG.write_text(text, encoding="utf-8")

    lines = [
        "# Freeze record", "",
        f"Frozen at (UTC): {ts}  ",
        f"prereg.yaml SHA-256: `{sha256(PREREG)}`", "",
        "Any change to `config/prereg.yaml` after this point must be logged in "
        "`outputs/deviation_log.md` before the affected analysis is run. "
        "`python scripts/freeze.py --verify` checks the hashes below.", "",
        "## Raw inputs (from data/raw/MANIFEST.csv)", "", "| path | bytes | sha256 |", "|---|---|---|",
    ]
    lines += [f"| {r['path']} | {r['bytes']} | `{r['sha256']}` |" for r in read_csv(MANIFEST)]
    lines += ["", "## Pre-analysis check outputs", "", "| path | sha256 |", "|---|---|"]
    outs = sorted((ROOT / "outputs" / "audit").glob("*")) + sorted((ROOT / "outputs" / "validation").glob("*"))
    lines += [f"| {p.relative_to(ROOT).as_posix()} | `{sha256(p)}` |" for p in outs if p.is_file() and p.name != ".gitkeep"]
    RECORD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"FROZEN at {ts}\nRecord: {RECORD.relative_to(ROOT)}")
    return 0


def verify() -> int:
    if not RECORD.exists():
        print("No freeze record found.")
        return 1
    rec = RECORD.read_text(encoding="utf-8")
    m = re.search(r"prereg\.yaml SHA-256: `([0-9a-f]{64})`", rec)
    problems = []
    if not m or m.group(1) != sha256(PREREG):
        problems.append("config/prereg.yaml changed since freeze -> log it in outputs/deviation_log.md")
    for path, digest in re.findall(r"^\| (data/raw/\S+) \| \d+ \| `([0-9a-f]{64})` \|$", rec, flags=re.M):
        p = ROOT / path
        if not p.exists() or sha256(p) != digest:
            problems.append(f"raw input changed or missing: {path}")
    if problems:
        print("VERIFY FAILED:\n  - " + "\n  - ".join(problems))
        return 1
    print("VERIFY OK: prereg.yaml and raw inputs match the freeze record.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    sys.exit(verify() if ap.parse_args().verify else freeze())
