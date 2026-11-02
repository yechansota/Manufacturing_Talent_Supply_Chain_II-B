"""
================================================================================
 Manufacturing Talent Supply Chain II-B — From the Production Line to Maintenance
 Pre-registered as "From the Line to Maintenance" (config/prereg.yaml, frozen 2026-10-18)
 U.S. motor vehicle parts manufacturing, NAICS 3363
================================================================================

 Runs every step in order, stops at the first failure, and writes the complete
 console output to results_log.txt.

 DATA REQUIRED (all free, no login) — see docs/DATA_DOWNLOAD_GUIDE.md
   data/raw/onet/  knowledge.csv, abilities.csv, essential_skills.csv,
                   transferable_skills.csv            (O*NET 31.0, CSV; registered)
   data/raw/oews/  oesm25in4.zip                      (OEWS May 2025, by industry; registered)
   data/raw/ep/    occupation.xlsx, education.xlsx,
                   nem-onet-to-soc-crosswalk.xlsx     (BLS EP 2025–35; registered)
   data/raw/onet/  training_and_experience.csv, training_and_experience_categories.csv,
                   job_zones.csv, job_zone_reference.csv   (O*NET 31.0; practice layer, DL-21)
   data/raw/ep/    National_Employment_Matrix_IND_336300.csv  (BLS NEM export; DL-23)
   data/raw/ces/   CEU3133630001 monthly export (BLS xlsx or FRED CSV; DL-26)
   data/raw/oews_history/  oesm21in4.zip … oesm24in4.zip (OEWS May 2021–2024; DL-29)
   data/raw/cps/basic/   jan20pub.zip … sep26pub.zip (CPS basic monthly); data/raw/census_codes/ (DL-37)

 Every analysis choice is read from config/prereg.yaml (frozen). Implementation
 readings of the frozen text and all post-hoc / exploratory items are logged in
 outputs/deviation_log.md (DL-1 … DL-48).

 Usage:   python run_pipeline.py            # full run (registered + review bootstraps, B = 1,000)
          python run_pipeline.py --quick    # every bootstrap with 50 draws (smoke test only; output audit skipped)
================================================================================
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "results_log.txt"

STEPS = [
    ("DATA CHECK — files present, SHA-256 manifest", ["scripts/check_downloads.py"]),
    ("FREEZE CHECK — prereg.yaml and raw inputs match the freeze record", ["scripts/freeze.py", "--verify"]),
    ("O*NET INGEST — schema, row counts, duplicates", ["-m", "src.ingest_onet"]),
    ("AUDIT — crosswalk, coverage, stop rule, SE gaps", ["-m", "src.audit"]),
    ("OEWS NAICS 336300 — frame re-validation", ["-m", "src.ingest_oews"]),
    ("BLS EP 2025–35 — tables and O*NET-SOC crosswalk check", ["-m", "src.ingest_ep"]),
    ("POINT ESTIMATES — D, P, C, H2 residuals, validity check", ["-m", "src.reference"]),
    ("DATA INTEGRITY REVIEW", ["-m", "src.integrity"]),
    ("PARAMETRIC BOOTSTRAP — H1 decisions, H1-group, N_eff (exploratory)", ["-m", "src.bootstrap"]),
    ("MULTIVERSE — 96 specifications per domain", ["-m", "src.multiverse"]),
    ("DESCRIPTIVE LAYERS — wage, EP demand, regulatory gates, decision table", ["-m", "src.layers"]),
    ("PRACTICE LAYER — top-10 ranking, pool, BLS factors, training time, gap matrix, NEM 336300, pathway table (DL-12–14, 21, 23, 25)", ["-m", "src.practice"]),
    ("OBSERVED TREND — CES employment, NAICS 3363 (DL-26; optional input)", ["-m", "src.trend"]),
    ("OBSERVED MIX — OEWS May 2021–2025 inside NAICS 3363: maintenance family and close-feeder pool (DL-29, 32)", ["-m", "src.history"]),
    ("CPS OBSERVED MOVES — production → maintenance in matched months; origin of entrants; allocation diagnostic; 3363 scale illustration, M codes by sector (DL-37, 40, 42, 43, 45, 46; optional input)", ["-m", "src.cps_moves"]),
    ("REVIEW SENSITIVITY — distances, Abilities subgroups, vintage (DL-16, 17, 20)", ["-m", "src.sensitivity", "--part", "point"]),
    ("REVIEW SENSITIVITY — correlated-error bootstrap, copula (DL-15a)", ["-m", "src.sensitivity", "--part", "bootstrap_copula"]),
    ("REVIEW SENSITIVITY — fully correlated errors, rho = 1 (DL-15b)", ["-m", "src.sensitivity", "--part", "bootstrap_comonotone"]),
    ("REVIEW SENSITIVITY — imputed-SE bootstrap and breadth indices (DL-18, 19)", ["-m", "src.sensitivity", "--part", "bootstrap_mi"]),
    ("REVIEW SENSITIVITY — summary", ["-m", "src.sensitivity", "--part", "summary"]),
    ("ROBUSTNESS — element split-half, leave-one-out, H2 functional form, FDR on H1, family + 49-1011 (DL-27, 32, 35)", ["-m", "src.robustness"]),
    ("FIGURES", ["scripts/make_figures.py"]),
    ("OUTPUT AUDIT — cross-path checks of every derived output (E1–E24)", ["-m", "src.output_audit"]),
]


def banner(text: str) -> str:
    line = "=" * 78
    return f"\n{line}\n  {text}\n{line}\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the full pipeline and write results_log.txt")
    ap.add_argument("--quick", action="store_true", help="bootstrap with 50 draws (not for reporting)")
    args = ap.parse_args()
    out = [banner("II-B FROM THE PRODUCTION LINE TO MAINTENANCE — FULL PIPELINE"),
           f"Started (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
           "Industry: NAICS 336300 Motor Vehicle Parts Manufacturing (national)\n"
           "Inputs: O*NET 31.0 · OEWS May 2025 · BLS Employment Projections 2025–35\n"]
    ok = True
    for title, cmd in STEPS:
        if args.quick and (cmd[-1] in ("src.bootstrap", "src.cps_moves") or cmd[-1].startswith("bootstrap_")):
            cmd = cmd + ["--draws", "50"]
            title += "  [QUICK: 50 draws — not for reporting]"
        if args.quick and cmd[-1] == "src.output_audit":
            continue
        t0 = time.time()
        res = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        out.append(banner(title))
        out.append(res.stdout)
        if res.stderr.strip():
            out.append("[stderr]\n" + res.stderr)
        out.append(f"-> exit {res.returncode} ({time.time() - t0:.1f} s)\n")
        print(f"[{'OK' if res.returncode == 0 else 'FAIL'}] {title} ({time.time() - t0:.1f} s)")
        if res.returncode != 0:
            ok = False
            break
    out.append(banner("PIPELINE " + ("COMPLETED" if ok else "STOPPED — see the failing step above")))
    LOG.write_text("".join(out), encoding="utf-8")
    print(f"Log written to {LOG.name}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
