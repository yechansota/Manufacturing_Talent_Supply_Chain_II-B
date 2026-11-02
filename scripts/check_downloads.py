"""Check that raw downloads are in the right folders and write a checksum manifest.

Run from the repo root:
    python scripts/check_downloads.py

Expected file names come from config/prereg.yaml (data_versions). Prints PASS /
MISSING for each item and writes data/raw/MANIFEST.csv (path, bytes, SHA-256,
timestamp). Raw files are never modified.
"""
from __future__ import annotations

import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import load_config  # noqa: E402

RAW = ROOT / "data" / "raw"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_files(cfg) -> list[tuple[str, str]]:
    dv = cfg["data_versions"]
    out = [("onet", spec["file"]) for spec in dv["onet"]["files"].values()]
    out.append(("oews", dv["oews"]["file"]))
    for key in ("occupation_file", "education_file", "crosswalk_file"):
        out.append(("ep", dv["ep"][key]["file"]))
    return out


def main() -> int:
    cfg = load_config()
    ok = True
    for folder, name in expected_files(cfg):
        p = RAW / folder / name
        status = "PASS" if p.exists() and p.stat().st_size > 0 else "MISSING"
        ok &= status == "PASS"
        print(f"  [{status}] data/raw/{folder}/{name}")

    rows = []
    for f in sorted(RAW.rglob("*")):
        if f.is_file() and f.name not in {"MANIFEST.csv", "README.md", ".gitkeep"}:
            rows.append({
                "path": f.relative_to(ROOT).as_posix(),
                "bytes": f.stat().st_size,
                "sha256": sha256(f),
                "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
    with open(RAW / "MANIFEST.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256", "checked_at_utc"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nManifest written: data/raw/MANIFEST.csv ({len(rows)} files)")
    print("RESULT:", "ALL REQUIRED FILES PRESENT" if ok else "SOME FILES MISSING — see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
