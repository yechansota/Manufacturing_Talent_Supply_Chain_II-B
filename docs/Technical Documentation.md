# Technical Documentation

## Manufacturing Talent Supply Chain II-B: From the Production Line to Maintenance (NAICS 3363)

Pre-registration: `config/prereg.yaml` v0.3, frozen 2026-10-18T19:11:28Z (`outputs/freeze_record.md`), registered under
the project name *From the Line to Maintenance*; it covers this repository's production → maintenance KSA analysis.
Every implementation reading of the frozen text and every post-hoc or exploratory item: `outputs/deviation_log.md`.
The exploratory floor map, the BLS projection layer, the projection track record and the CPS age profile and flows
moved to the companion repository II-A (*Where Each Floor Job's Successors Come From*) when the project was split
(DL-36, DL-47); their log entries stay here because this log is never edited.

---

## Table of Contents
1. System Architecture
2. Data Pipeline
3. Analysis Frame
4. Estimands
5. Uncertainty — Parametric Bootstrap
6. Robustness — Multiverse
7. Descriptive Layers
8. Data Integrity Review
9. Deviation Log Summary
10. Code Reference
11. Troubleshooting
12. Practice Layer (DL-12 – DL-14, DL-21, DL-23, DL-25, DL-26, DL-28)
13. Review-Stage Sensitivity Analyses (DL-15 – DL-20)
14. Output Audit (E1 – E24) and DL-22
15. Element and Target Robustness (DL-27)
16. Observed Mix and the Close-Feeder Pool (DL-29)
17. Multiple Comparisons and Endpoints (DL-32)
18. The 49-1011 Sensitivity (DL-35)
19. Observed CPS Moves and the Headline Rule (DL-37, DL-40, DL-42)
20. Origin of Maintenance Entrants, Scale Illustration and Where the Maintenance Occupations Work (DL-43, DL-45, DL-46)
21. Repository Split: Mapping Tables (DL-36, DL-47, DL-48)
- Appendix A: Environment Setup (macOS + Anaconda)
- Appendix B: Requirements

---

## 1. System Architecture

### 1.1 Overview
```
data/raw (8 registered public files + optional inputs: O*NET training files, NEM export, CES export,
          OEWS May 2021–2024, CPS 2020–2026 and Census code lists; SHA-256 of every file in MANIFEST.csv)
   │  scripts/check_downloads.py ── scripts/freeze.py --verify
   ▼
src.ingest_onet ─► DuckDB onet_ratings        (schema, row/occupation/element counts)
src.audit       ─► outputs/audit/             (crosswalk, coverage, stop rule, SE gaps)
src.ingest_oews ─► DuckDB oews_3363           (frame re-validation on May 2025)
src.ingest_ep   ─► DuckDB ep_*                (EP 2025–35, BLS crosswalk cross-check)
   ▼
src.reference   ─► outputs/estimates/point_*  (D, P, C, H2 residuals, validity)
src.integrity   ─► outputs/review/            (16 cross-source checks)
src.bootstrap   ─► outputs/estimates/bootstrap_*, h1_*, neff_exploratory.csv
src.multiverse  ─► outputs/multiverse/        (96 specs per domain)
src.layers      ─► outputs/layers/            (wage, EP, regulatory gates, decision table)
src.practice    ─► outputs/practice/          (top-10 ranking, pool, BLS factors, training time, gap matrix, NEM 336300, pathway table)
src.trend       ─► outputs/practice/ces_*     (observed CES employment, DL-26)
src.sensitivity ─► outputs/sensitivity/       (error models, distances, Abilities subgroups, vintage)
src.history     ─► outputs/history/           (OEWS May 2021–2025 inside 3363, close-feeder pool; DL-29, DL-36e)
src.cps_moves   ─► outputs/cps_moves/         (matched CPS months: Q1–Q3, origin of entrants, scale illustration; DL-37, 40, 42, 43, 45, 46)
src.robustness  ─► outputs/robustness/        (element split-half, leave-one-out, H2 functional form, FDR on H1, family + 49-1011; DL-27, 32, 35)
scripts/make_figures.py ─► figures/           (fig1–fig8, figS1)
src.output_audit ─► outputs/review/output_audit.*  (E1–E24 cross-path checks)
```
`run_pipeline.py` runs all steps in this order, stops at the first failure, and writes `results_log.txt`.
Neither repository reads the other's code or outputs (DL-36a).

### 1.2 Consistency guards
- The bootstrap re-evaluates the point estimate through its own code path and stops if it differs from
  `point_pairs.csv` by more than 1e-8.
- The multiverse primary specification must reproduce `point_pairs.csv` exactly.
- Ingest steps fail on any header, row-count, version-title or crosswalk mismatch (`strict_version_check: true`).
- Review-stage paths assert that they reproduce the registered P before reporting anything else: the continuous-
  distance path, the Abilities `all` subgroup and the vintage path at `min_year = 0`.

### 1.3 Configuration
All analysis choices live in `config/prereg.yaml` (frame, crosswalk overrides, scales, weights, decision rules,
multiverse grid, prohibited uses). Code never branches on choices that are not in that file.

---

## 2. Data Pipeline

### 2.1 O*NET 31.0 (CSV)
| File | Domain | Rows | Elements | Rater |
|---|---|---|---|---|
| knowledge.csv | K | 60,060 | 33 | Incumbent 653 / Occupational Expert 248 / Analyst-Transition 9 occupations |
| abilities.csv | A | 94,640 | 52 | Analyst |
| essential_skills.csv | S | 18,200 | 10 | Analyst |
| transferable_skills.csv | S | 45,500 | 25 | Analyst |

Rows = 910 occupations × elements × 2 scales (Importance IM 1–5, Level LV 0–7). Columns used: value, N, SE,
CI bounds, Recommend Suppress, Not Relevant, Date, Domain Source. In release 30.3 the single Skills file was split
into Essential and Transferable Skills; S is their union (35 elements).

Validation results: header exact; counts exact; no duplicates; values inside scale ranges; published CI half-width
/ SE = 1.96 (median); "Not Relevant" rows have median Importance 1.00; "Recommend Suppress" rows have higher SE.

### 2.2 OEWS May 2025, national industry-specific
Read directly from `oesm25in4.zip` → `nat4d_M2025_dl.xlsx`; `AREA = 99`, `NAICS = 336300`; total employment
538,980 (checked). Non-numeric tokens (`*`, `**`) become missing with the raw token kept in `<col>_raw`.
OEWS publishes 51-2090 (and 13-1020) both as a broad and a detailed row with identical values; one row is kept.

### 2.3 BLS Employment Projections 2025–35
- `occupation.xlsx` → Table 1.10 (separations and openings, annual averages); title must contain "2025–35".
- `education.xlsx` → Table 5.4 (entry education, related work experience, typical OJT). Read with
  `keep_default_na=False` so the category "None" stays text.
- `nem-onet-to-soc-crosswalk.xlsx` → "As of 08/27/2026" required.

Identity check: openings = separations + employment change / 10 holds to rounding (max 0.10k over 831 line items).

### 2.4 Crosswalk cross-check
For every frame SOC code, every O*NET code BLS assigns to it must be mapped in `prereg.yaml` (primary or
sensitivity) or listed in `excluded_codes` with a reason. Result: 23/23 OK. One-to-many cases:
51-2028 → 51-2022.00 + 51-2023.00 (equal-weight profile mean); 51-2090 → 51-2092.00 (51-2099.00 excluded, no
ratings); 17-3024 → .00 (.01 sensitivity); 17-3026 and 53-7062 → .00 (the .01 / .04 codes excluded as distinct
occupations).

---

## 3. Analysis Frame
Selected by rule on OEWS May 2025 (NAICS 336300), before any KSA computation.

| Role | Rule | Codes |
|---|---|---|
| Target (core) | maintenance/repair/electrical function; employment ≥ 1,000, RSE < 10% | 49-9041, 49-9071, 47-2111, 49-9043, 49-9044 |
| Target (sensitivity) | below the rule | 49-2094, 17-3024 |
| Feeder (core) | SOC 51 detailed, employment ≥ 4,000, RSE < 10%, not "All Other" | 51-2090, 51-4031, 51-2031, 51-9061, 51-4121, 51-4081, 51-4041, 51-2028, 51-9161, 51-4072, 51-4122, 51-9124 |
| Sensitivity | meets the rule but excluded by design, or outside SOC 51 | 51-1011, 51-4111, 17-3026 |
| Negative control | expected to be far | 53-7062 |

The rule is re-applied mechanically in `src.ingest_oews`; any occupation that meets it without being in the frame
(and without a documented design exclusion) stops the run.

---

## 4. Estimands
Per domain d ∈ {K, S, A}; never summed across domains. Reference universe 𝒰 = all 910 rated occupations.

**Standardization** (primary): $z_{ok} = (L_{ok} - \bar L_k)/s_k$ over 𝒰 (sample SD).

**Weights:** $w_{jk} = I_{jk} - 1 \in [0, 4]$ (Importance of the target).

**Maintenance family J:** $z_{Jk} = \sum_j \pi_j z_{jk}$, $w_{Jk} = \sum_j \pi_j w_{jk}$, with $\pi_j$ = OEWS 3363
employment share (49-9041 48.3%, 49-9071 29.9%, 47-2111 10.7%, 49-9043 6.2%, 49-9044 4.9%).

**Contribution and directional deficit:**

$$
c_{ijk} = w_{jk}\,\max(0,\; z_{jk} - z_{ik}), \qquad
D(i \to j) = \frac{\sum_k c_{ijk}}{\sum_k w_{jk}}
$$

**Proximity percentile (H1):** with reference set $R = \mathcal{U} \setminus \{\text{members of } j\}$,

$$
P(i \to j) = \frac{100}{|R|} \sum_{o \in R} \mathbf{1}\big[D(o \to j) \le D(i \to j)\big]
$$

**Concentration (H2, primary):** $C^{(5)} = \sum_{r=1}^{5} c_{ij(r)} \,/\, \sum_k c_{ijk}$. H2 compares C with
occupations of the same total deficit: OLS $C = a + bD$ over $o \in R$ with $D > 0$ (log D as sensitivity); a
feeder supports H2 when its residual exceeds the 95th percentile of the reference residuals.

**Breadth (exploratory, DL-9):** $N_{\text{eff}} = 1 / \sum_k s_k^2$, $s_k = c_{ijk} / \sum_k c_{ijk}$.

Checked properties (unit tests): $D(j \to j) = 0$; $D \ge 0$; $0 \le C \le 1$; P and C invariant to a common
rescaling of z.

---

## 5. Uncertainty — Parametric Bootstrap
B = 1,000, seed 20261003. Each draw samples every Level and Importance rating from a normal truncated to its scale
(LV [0, 7], IM [1, 5]) with the published SE, then recomputes z, all profiles, the reference set, both fits and q95.
π is fixed. Knowledge rows without a published SE (16,962 cells) receive the median SE of incumbent-rated
occupations for the same element × scale.

- H1 rule: 97.5th percentile of P ≤ 25.
- Monte Carlo error: split-half difference of the bound / 2 (max 1.67 points); a second seed (777) changed no H1
  decision.
- Centering: bootstrap mean D − point D, median +0.029 (K), −0.009 (S), −0.004 (A) — truncation near zero.
- Known limitation: draws are independent across elements.

---

## 6. Robustness — Multiverse
3 standardizations × 2 weights × 2 suppress rules × 2 not-relevant rules × 2 feeder thresholds × 2 family weights
= 96 specifications per domain (family target, point estimates). Implementation of each branch and the summary
metrics are fixed in DL-11 (logged before the run). H2 is "supported" in a specification when at least k* feeders
exceed q95, with k* the smallest k such that P(X ≥ k) < 0.05 for X ~ Binomial(n, 0.05) (k* = 3 for n = 12, 14).

---

## 7. Descriptive Layers
Reported beside the KSA results, never combined into an index.
- **Wage:** OEWS 3363 median hourly wage; family value = employment-weighted mean of target medians (approximation).
- **Demand:** EP 2025–35 openings, separation, exit and transfer rates; entry education and typical OJT.
- **Regulatory gates (verified on osha.gov, 2026-10-18):**
  - 29 CFR 1910.147(b) defines *authorized* (locks/tags out to service) and *affected* (operates) employees;
    (c)(7)(i)(A) requires authorized-employee training in hazardous energy recognition, type and magnitude, and
    isolation; (c)(7)(i)(B) requires only instruction for affected employees.
  - 29 CFR 1910.332(b)(3): qualified persons (on or near exposed energized parts) are trained to distinguish live
    parts, determine nominal voltage and know clearance distances.
  - 29 CFR 1910.399, "Qualified person", Note 2: a trainee who has demonstrated safe performance at his or her level
    and is directly supervised by a qualified person is considered qualified for those duties.
  - 29 CFR 1910.147(b) defines servicing to include setting up, adjusting and tool changes; the (a)(2)(ii) Note exempts
    routine minor servicing done with alternative protection.
  - Applicability per occupation (`outputs/layers/regulatory_gates.csv`) is an analyst reading of occupational
    function, grounded in O*NET Importance of Repairing and Equipment Maintenance: feeders whose higher value is
    ≥ 3.0 are coded "may already be authorized for the equipment it sets up or services" (DL-24). It must be validated
    against plant job descriptions.

---

## 8. Data Integrity Review
`outputs/review/integrity_review.md` — 16 checks. All source-fidelity checks (A1–A7) and the classification link
(B1) pass. Disclosed notes: rating vintage, industry scope, mixed K raters, family-weight concentration, 51-2090
proxy share, 51-2028 two-vintage profile, K directional-deficit semantics, C–D fit shape (R² 0.20–0.71). Flag: the
negative control fails in Abilities (H1 not interpreted there).

---

## 9. Deviation Log Summary
| ID | Type | Content |
|---|---|---|
| DL-1–6 | clarification | Family reference excludes its five members; H2 unit = feeder → family per domain; linear fit primary + log sensitivity; residual-percentile construction; validity scope per domain; sample SD |
| DL-7 | post-hoc diagnostic | D-matched local percentile of C (robustness of the H2 fit) |
| DL-8 | clarification (not blind) | H1-group membership and permutation statistic |
| DL-9 | exploratory addition | N_eff |
| DL-10 | clarification | Bootstrap details (SE imputation, truncation, MC error, H2 decision basis) |
| DL-11 | clarification | Multiverse branch implementation and summary metrics |
| DL-12 | exploratory addition | Top-10 ranking of all SOC-51 occupations employed in 3363 (outside the registered frame) |
| DL-13 | descriptive addition | Pool arithmetic: close pool vs. family employment and illustrative separations |
| DL-14 | descriptive addition | BLS EP Table 1.12 factors (336300 row, else all-industry row, else none) |
| DL-15 | sensitivity addition | Correlated measurement error: Gaussian copula (seed 20261004) and ρ = 1 (seed 20261005) |
| DL-16 | sensitivity addition | Continuous distances: directional D, weighted Euclidean, Ledoit–Wolf Mahalanobis |
| DL-17 | exploratory addition | Abilities subgroups (cognitive 21, psychomotor 10, physical 9, sensory 12) and classical MDS |
| DL-18 | sensitivity addition | Breadth alternatives exp(Shannon) and k80 with bootstrap intervals |
| DL-19 | sensitivity addition | Random-draw (multiple-imputation style) Knowledge SEs inside the bootstrap (seed 20261006) |
| DL-20 | sensitivity addition | Drop occupations rated before 2018 (erratum: universe spans 2004–2026) |
| DL-21 | exploratory addition | O*NET training-time layer (OJ, PT, RW categories; Job Zones) |
| DL-22 | correction | Output-audit fixes: self-tie tolerance in non-registered modules; withheld employment flagged; Table 1.12 "no entry" labels; no registered value changed |
| DL-23 | descriptive addition (new input) | BLS National Employment Matrix for NAICS 336300: projected change inside the industry |
| DL-24 | correction (descriptive layer) | Lockout/tagout coding for feeders grounded in O*NET Importance of Repairing / Equipment Maintenance; setters may already be authorized |
| DL-25 | descriptive and audit additions | Close-pool transfer flow, pathway table, E15 (NEM vs OEWS staffing pattern), E16 (independent recomputation) |
| DL-26 | descriptive addition (new input) | Observed CES employment for NAICS 3363 (optional file in data/raw/ces; `src/trend.py`) |
| DL-27 | post-hoc robustness addition | Element split-half, leave one element / target out, H2 functional forms (`src/robustness.py`); first run ad hoc, logged before the module run |
| DL-28 | descriptive addition | Two-stage reading of NEM 336300 (industry baseline + BLS adjustment); Table 1.12 automation factors counted per occupation; single-repository Figure 6 redrawn (now II-A Figure 3) |
| DL-29 | descriptive addition (new inputs) | OEWS May 2021–2024 + EP industry workbook: observed mix inside 3363, 2021–2025 (`src/history.py`), industry output (`industry_output`) |
| DL-30 | exploratory addition (new inputs) | O*NET Software Skills and Task Statements: skill content inside the maintenance family (II-A, `src/skill_shift.py`) |
| DL-31 | exploratory addition | Succession bench for every floor position with ≥ 1,000 jobs; successor = lower-paid role with the same or lower Job Zone (II-A, `src/floor_map.py`) |
| DL-32 | registered setting + robustness | Benjamini–Hochberg at the registered `fdr_q` on H1 and the skill-shift tests; 2022 endpoint and premium z for the OEWS changes; floor-map bootstrap and rule variants |
| DL-33 | descriptive addition | Cross-part link columns in the floor map; README chapter 4 reordered Part 1 → 2 → 3 with bridges |
| DL-34 | descriptive addition | BLS adjustment by O*NET Job Zone for all 181 NEM 336300 line items; single-repository Figure 12 (now II-A Figure S1) |
| DL-35 | disclosure + sensitivity; log wording | 49-1011 meets the target thresholds but is not registered (no reason recorded); P with 49-1011 added to the family; reviewer attributions replaced by 'added after the point estimates as a sensitivity analysis' |
| DL-36 | repository organization | Split into II-A (Parts 1–2) and II-B (Part 3); no repository reads the other's outputs; this log kept complete |
| DL-37 | exploratory addition (planned) | Observed production → maintenance moves in matched CPS months; plan logged before any CPS file was obtained |
| DL-38 | descriptive addition (planned) | Track record of BLS projections for NAICS 3363 (industry and 2014–24 occupations); plan logged before the archive files were obtained |
| DL-39 | correction + scope decision | README 'most adjustments cite automation' replaced by the count (42 of 86 adjusted line items, 49.8% of adjusted jobs); scope note in the log |
| DL-40 | clarification + one added check | Readings of DL-37 and DL-38 fixed before computing: Q2 read by destination, Census code groups, linking rules, persistence rule, NCHS rule with bootstrap intervals; added check (iv) allocated codes |
| DL-41 | disclosure after results | The 2014–24 occupation comparison crosses the OEWS 2018 SOC hybrid years and the 2021 MB3 method change; not used to judge BLS occupational projections |
| DL-42 | post-hoc interpretive change | README CPS headline = estimate without allocated codes (check iv); registered primary beside it; allocation diagnostic written to file |
| DL-43 | exploratory addition | Origin composition of maintenance entrants in manufacturing (seven t−1 occupation groups); origins 1 + 2 = Q2 |
| DL-44 | exploratory addition | Age profile (A1), destinations of production workers (A2), maintenance inflow and outflow (A3) for manufacturing; runs in II-A after the split |
| DL-45 | descriptive addition (post-hoc illustration) | Q1 per 10,000 and annualized; illustrative NAICS 3363 scale of the same-employer rate beside the family's illustrative separations |
| DL-46 | descriptive addition | National employment of the M-code SOCs by NAICS sector (OEWS May 2025) and their manufacturing share, for reading Q1 |
| DL-47 | repository organization | Split executed: this repository is II-B; figures renumbered 1–8 and S1; audit checks renumbered |
| DL-48 | audit addition | Two-stage NEM check kept here as E24 (adjustment column of `nem_336300.csv`) |

The analyses of DL-28 (automation counts), DL-29 (industry output), DL-30, DL-31 – DL-33 (floor map parts), DL-34, DL-38, DL-39(a), DL-41 and DL-44 run in II-A, which carries verbatim copies of those entries; they stay in this log because no entry is removed (DL-36b).

One coding error was found and fixed during the run: the point-estimate module counted D = 0 occupations in the
denominator of the H2 residual percentile. The bootstrap consistency guard caught it; the fix changed the K median
from 5.25 to 5.26 and no decision.

---

## 10. Code Reference
| Module | Purpose |
|---|---|
| `src/frame.py` | roles, SOC → O*NET resolution, aggregation rules |
| `src/ingest_onet.py`, `src/ingest_oews.py`, `src/ingest_ep.py` | validated ingest into DuckDB |
| `src/audit.py` | coverage, stop rule, SE gaps, collection years |
| `src/deficit.py` | pure estimator functions (z, c, D, C, P, OLS) |
| `src/profiles.py`, `src/reference.py` | profiles and point estimates |
| `src/bootstrap.py` | parametric bootstrap, H1 rule, H1-group test, N_eff |
| `src/multiverse.py` | 96-spec grid with pairwise deletion for dropped cells |
| `src/layers.py` | wage, EP, regulatory gates, decision table |
| `src/integrity.py` | cross-source integrity review |
| `src/practice.py` | practice layer: production ranking, pool arithmetic, BLS factors, training time, gap matrix, NEM 336300 projection (two-stage columns, DL-28), pathway table |
| `src/sensitivity.py` | review-stage sensitivity analyses (error models, distances, Abilities subgroups, vintage) |
| `src/output_audit.py` | E-checks E1–E24: re-derivation and cross-path agreement of every downstream output |
| `scripts/make_figures.py` | Figures 1–8 and S1 from the outputs |
| `scripts/independent_check.py` | independent re-implementation of the core estimands from the raw files (E16) |
| `src/trend.py` | observed CES employment, NAICS 3363: monthly series and annual averages (DL-26) |
| `src/robustness.py` | element split-half, leave one element / target out, H2 functional forms (DL-27); `bh_adjust`, `fdr_h1` (DL-32); `family_plus_supervisors` (DL-35) |
| `src/history.py` | OEWS May 2021–2025 inside 3363: employment, RSE, wages, maintenance mix, close pool, endpoint z (DL-29, DL-32) |
| `src/cps_moves.py` | matched CPS months: production → maintenance moves, Q1–Q3 and four checks (DL-37, DL-40); origin of entrants, allocation diagnostic, units and 3363 scale illustration (DL-42, 43, 45) |

---

## 11. Troubleshooting
| Message | Cause | Fix |
|---|---|---|
| `header mismatch` / `rows=… expected=…` | wrong O*NET release or a file re-saved in Excel | re-download O*NET 31.0 CSVs |
| `title does not contain '2025–35'` | older EP workbook | download the current EP tables |
| `meets the feeder rule but is not in feeders_core` | different OEWS release | use May 2025, or log a deviation and update the frame |
| `VERIFY FAILED` | a raw file or prereg.yaml changed | stop; record the change in `outputs/deviation_log.md` |
| `knowledge_1.csv` / `knowledge (1).csv` | browser renamed the download | rename to `knowledge.csv` |

---

## Appendix A: Environment Setup (macOS + Anaconda)
```bash
cd path/to/repo
/opt/anaconda3/bin/python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py
```

## Appendix B: Requirements
`pandas`, `numpy`, `duckdb`, `PyYAML`, `openpyxl`, `scipy`, `matplotlib`, `tabulate`, `scikit-learn`
(Ledoit–Wolf covariance), `pytest` — versions in `requirements.txt`.

---

---

## 12. Practice Layer (DL-12 – DL-14, DL-21, DL-23, DL-25, DL-26, DL-28)
`python -m src.practice` → `outputs/practice/`. Point estimates and descriptive tables; nothing here is a
registered hypothesis.
- **Production ranking** (`production_ranking_3363.csv`, `top10_{S,K,A}.csv`): every SOC-51 detailed occupation
  with OEWS 3363 employment (53) and an O*NET profile (51; 51-4199 and 51-9199 have none). D and P against the family
  with the frozen reference set. `small_or_imprecise` = fewer than 1,000 jobs, employment RSE ≥ 10%, or employment
  withheld (51-9123).
- **Pool arithmetic** (`pool_arithmetic.csv`): family employment, the Skills close pool (feeders meeting H1),
  illustrative separations = 3363 employment × EP all-industry separation rate per target.
- **BLS factors** (`bls_factors.csv`): EP Table 1.12 text from the NAICS 336300 row, else the all-industry (TE1000)
  row, else `no entry`; for `no entry`, the other industries with a factor are listed.
- **Training time** (`training_time.csv`): O*NET Training & Experience category percentages (OJ, PT 9 categories;
  RW 11). Equal-weight mean over the O*NET codes behind a SOC; median category = first category whose cumulative
  share reaches 50%; "over 1 year" = categories ≥ 6 on all three scales (labels verified in E6). Family values are
  employment-weighted with π.
- **Within-industry projections** (`nem_336300.csv`, DL-23): BLS National Employment Matrix export for NAICS 336300
  (`data/raw/ep/National_Employment_Matrix_IND_336300.csv`; codes written as `="xx-xxxx"` are unquoted; employment in
  thousands as published). For targets, feeders and context occupations: 2025 and 2035 employment, change, percent of
  industry, and percent change minus the industry's (−13.9%). Optional input: the step is skipped with a note if the
  file is absent. The NEM 2025 base (524.7k) is not mixed with OEWS (538,980) in any ratio.
  **Two-stage reading (DL-28):** `baseline_change_pct` = the modal percent change among the 181 line items
  (−12.9%, 95 items, 65% of 2025 jobs); `bls_adjusted` = change ≠ baseline; `bls_adjustment_pct`
  $= 100\,[(1 + c/100)/(1 + b/100) - 1]$. The baseline set is exactly the set of line items without a Table 1.12 row
  for 336300 or all industries (E24), which is what the BLS share-rescaling method implies.
- **Pathway table** (`pathway_table.csv`, DL-25b): per core feeder, Skills P upper bound, 3363 jobs, change inside
  3363, wage gap, own OJT median, BLS typical OJT, transfer rate and the higher servicing Importance, side by side.
- **Close-pool transfers** (row of `pool_arithmetic.csv`, DL-25a): 3363 employment × EP occupational transfer rate for
  the Skills close feeders; destination unknown.
- **Observed trend** (`ces_3363_monthly.csv`, `ces_3363_annual.csv`, DL-26; `src/trend.py`): BLS CES CEU3133630001,
  not seasonally adjusted, thousands. Annual average = mean of 12 months; incomplete years flagged. The 2025 average
  (524.69k) equals the NEM 2025 base (524.7k), consistent with CES supplying the NEM industry total.
- **Gap matrix** (`gap_matrix.csv`): per element, $w_k \max(0, z_{\text{family},k} - z_{f,k}) / \sum_k w_k$; sums to D.

## 13. Review-Stage Sensitivity Analyses (DL-15 – DL-20)
`python -m src.sensitivity --part point|bootstrap_copula|bootstrap_comonotone|bootstrap_mi|summary`
→ `outputs/sensitivity/`. Each was logged before it was run.
- **Error models.** All draw truncated-normal marginals by inverse CDF of standard-normal scores.
  *Copula:* scores correlated within occupation × domain × scale with $R$ = cross-occupation Pearson correlation of
  the ratings (nearest positive-definite repair). *ρ = 1:* one score per occupation × scale. *MI-SE:* missing
  Knowledge SEs redrawn each replicate from incumbent-rated SEs of the same element × scale (S and A have no missing
  SE, so they differ from the registered run only by Monte Carlo noise; E4). B = 1,000 each.
- **Distances.** Directional D (registered), importance-weighted standardized Euclidean, Mahalanobis with a
  Ledoit–Wolf covariance of z over the 905 reference occupations. Point percentiles; Spearman rank agreement with D.
- **Abilities subgroups.** D and P recomputed within 1.A.1 – 1.A.4 with z over the full universe; family profile built
  on the full element set and sliced (DL-22). Classical MDS = first two principal coordinates of centered z.
- **Vintage.** Occupations whose earliest rating year is before 2018 are dropped from the universe and the frame
  (171 of 910; frame: 51-2031.00, 51-4072.00, 51-2023.00).

## 14. Output Audit (E1 – E24) and DL-22
`python -m src.output_audit` → `outputs/review/output_audit.{csv,md}`; exit code 1 if any check is FLAG. Rows are written
in id order. Numbering after the split (DL-47, DL-48); mapping to the single-repository numbers in section 21.
| ID | Check |
|---|---|
| E1 | Registered P: every self-tie exact, no other reference occupation within 1e-9 of a feeder D (384 pairs) |
| E2 | Feeder → family P identical across five code paths (registered, practice, distances, Abilities `all`, multiverse primary) |
| E3 | Error-model files: B, seed, ranges, feeder set; re-execution identical cell by cell |
| E4 | MI-SE changes Knowledge only; no H1 decision flips |
| E5 | Gap matrix sums to D; no negative cells |
| E6 | Training layer re-derived from the raw file; category sums = 100; "over 1 year" boundary labels |
| E7 | Production ranking coverage and employment against OEWS |
| E8 | Pool arithmetic re-derived from OEWS and EP |
| E9 | Table 1.12 factor text and levels against the raw workbook |
| E10 | Vintage exclusions equal the DL-20 list |
| E11 | Abilities subgroup sizes equal DL-17 |
| E12 | Deviation-log ids contiguous and unique |
| E13 | Figures newer than the outputs they draw (II-B figures) |
| E14 | NEM 336300: parse, Σ major groups = total, group = sum of parts, change = 2035 − 2025, % change recomputed, SHA-256 in MANIFEST |
| E15 | NEM 2025 vs OEWS May 2025 inside 3363: share correlation > 0.999, max share difference < 0.1 point, level ratio of occupations ≥ 5,000 jobs within 0.01 of the total ratio |
| E16 | `scripts/independent_check.py`: D, P, C for 16 frame occupations × 3 domains, π, family wage and pool re-derived from the raw files without project code |
| E17 | CES file: series id, not seasonally adjusted, consecutive months, annual averages re-derived, SHA-256 in MANIFEST; 2025 annual average equals the NEM 2025 total within 0.05k |
| E18 | Robustness: re-execution identical; leave-one-target-out P re-derived through `src.bootstrap.evaluate` (240 values, max difference 1.4e-14); negative control never P ≤ 25 in S/K half-sets |
| E19 | OEWS history: May 2021 and 2025 employment and mean wages re-read from the raw zips; 2025 equals the registered `oews_3363`; 2021–2024 SHA-256 in MANIFEST |
| E20 | Multiple comparisons and endpoints (DL-32): bootstrap p-values re-derived from the draw counts; BH re-derived by a step-up search for H1 (24 S/K tests); premium z of 49-9041 over the three close feeders re-derived from the yearly OEWS file for both start years |
| E21 | 49-1011 sensitivity (DL-35): the registered P column equals the point estimates; Skills P with 49-1011 added re-derived with pandas from the raw O*NET CSVs (tolerance one tie step, 100/904) |
| E22 | CPS observed moves (DL-37): all monthly files re-read with a dict-based linker; pairs and unweighted counts for Q1 and Q2 match the module |
| E23 | CPS additions (DL-42, 43, 45, 46): allocation diagnostic and origin counts re-derived in the same streaming pass; origin shares sum to 100% and origins 1 + 2 equal Q2 in all eight check × employer cells; annualization and scale illustration recomputed; M codes by sector re-read from the OEWS workbook with openpyxl |
| E24 | Two-stage NEM reading (DL-28, DL-48): baseline = mode; at baseline ⇔ no Table 1.12 row for 336300 or all industries (95 + 86 of 181); adjustments in `nem_336300.csv` re-derived |

**DL-22.** The reference set contains each feeder's own O*NET row, so P counts a self-tie by design. Building the
family profile from a column-sliced matrix changed D by about 1e-16 and dropped that tie for three Abilities feeders
(P lower by exactly 1/905). The non-registered modules now build on the full element set and compare with a
tolerance of 1e-12. E1 shows the registered modules are unaffected.

## 15. Element and Target Robustness (DL-27)
`python -m src.robustness` → `outputs/robustness/` (`element_splits.csv`, `leave_one_out.csv`, `h2_forms.csv`,
`domain_summary.csv`). Point estimates; z over the full universe, family profile built on all elements and then
sliced (DL-22), so the full element set reproduces the registered P (asserted).
- **Element split-half:** per domain, 500 random splits of the elements into two halves (seed 20261007); P of every
  frame feeder in each of the 1,000 half-sets; share with P ≤ 25 and the 5/50/95% quantiles; median and 5th-percentile
  Spearman correlation of core-feeder P between halves, Spearman–Brown of the median; share of splits in which both
  halves give the full-set top three.
- **Leave one element out / leave one target out:** P for every feeder; for a target, the family mix is renormalized
  over the remaining four and the removed target rejoins the reference set.
- **H2 functional form:** polynomial fits of degree 1–3 over reference occupations with D > 0, and a local 95th
  percentile among the 50 / 100 / 200 nearest in D; number of core feeders above, and below the local median.

| Result | Skills | Knowledge |
|---|---|---|
| Close feeders with P ≤ 25 in half-sets | 51-9161 98.9%, 51-4081 97.5%, 51-4041 95.9% | 51-2090 99.4%; 51-9161 71.5%; 51-9061 62.5% |
| Both halves give the full-set top three | 99.4% | 6.4% |
| Median split-half Spearman (Spearman–Brown) | 0.72 (0.84) | 0.93 (0.96) |
| Leave one element out | top three unchanged in 35/35; max P 12.0 | 51-2090 first in 33/33 |
| Leave one target out | top three unchanged in 5/5 | 51-2090 first in 5/5; top three unchanged in 4/5 |
| H2, all six forms | 0 of 12 above | 0 of 12 above |

## 16. Observed Mix and the Close-Feeder Pool (DL-29)
`python -m src.history` → `outputs/history/`. Inputs: `data/raw/oews_history/oesm21in4.zip` … `oesm24in4.zip` and the
registered `data/raw/oews/oesm25in4.zip`; member `nat4d_M<year>_dl.xlsx` read from the zip; columns upper-cased (the
2021 file uses lower case); NAICS 336300 only; numeric parsing and duplicate resolution as in the registered ingest.
- `oews_3363_2021_2025.csv`: every detailed occupation (plus 51-2090 and the total) × year: employment, employment RSE,
  hourly and annual means and medians.
- `maintenance_mix.csv`: per year, the five targets, the Skills close feeders, context occupations, the family and the
  close pool: employment, RSE, share of industry, share of family, annual median, mean hourly wage and its RSE, and the
  premium of 49-9041 over each target and close feeder on mean hourly wage (published RSE) and on annual median (no
  published error). Change 2021 → 2025 with $z = \Delta / \sqrt{SE_{2021}^2 + SE_{2025}^2}$, $SE$ = employment × RSE
  (independence assumed; each May estimate pools six semiannual panels over three years, so May 2021 and May 2025 share
  none). A 2022 → 2025 block and the z of each premium change were added in DL-32 (section 17).
- Industry output (DL-29b) runs in II-A. The close-feeder rows and the pool series stay here (DL-36e).

| Result (NAICS 3363) | 2021 | 2025 | Change |
|---|---|---|---|
| Maintenance family (5 targets) | 29,130 | 27,330 | −6.2% |
| 49-9041 industrial machinery mechanics | 11,770 (40.4% of family) | 13,210 (48.3%) | +12.2% (z 4.4) |
| 49-9043 machinery maintenance workers | 3,570 | 1,690 | −52.7% (z −15.4) |
| Close pool (51-9161, 51-4081, 51-4041) | 41,970 | 32,370 | −22.9% |
| 49-9041 mean-wage premium over 49-9043 / 49-9071 | +13.7% / +18.9% | +8.1% / +4.3% | |

## 17. Multiple Comparisons and Endpoints (DL-32)
Applies the registered `decision_rules.fdr_q` (0.05) that no earlier step used, and makes the review checks of
2026-10-21 reproducible. The skill-shift tests and the floor-map bootstrap and rule variants of DL-32 run in II-A.
- **H1 (`src/bootstrap.py`, `src/robustness.py`).** `h1_decisions.csv` gains `n_draws_P_above_thr` and
  $p = (\#\{P^{*} > 25\} + 1)/(B + 1)$; the registered bootstrap is re-run with its seed and every earlier column is
  identical. `fdr_h1(cfg)` → `outputs/robustness/fdr_h1.csv`: Benjamini–Hochberg adjusted p for the 24 core-feeder tests
  of S and K (primary family), for all 36 with A, and per domain; Bonferroni over the 24; `close_after_fdr` = registered
  rule and BH. Result: the four close decisions (S 51-9161, 51-4081, 51-4041; K 51-2090) have p = 1/1001, adjusted 0.006;
  no decision changes; K 51-9161 has p = 0.041 (adjusted 0.197).
- **OEWS history (`src/history.py`).** `PERIODS = ((2021, 2025), (2022, 2025))`; `change_rows` adds the 2022 → 2025 block
  and `premium_mean_change_z` $= \Delta \ln(w_{49\text{-}9041}/w_{c}) \,/\, (\sqrt{\sum \mathrm{RSE}^2}/100)$ over the
  four estimates. May 2021 / May 2022 and May 2025 estimates share no semiannual panel (each pools six panels over three
  years; [OEWS technical notes](https://www.bls.gov/oes/2025/may/oes_tec.htm)).

| Result | Value |
|---|---|
| H1 decisions changed by BH (q = 0.05, 24 tests) | 0 of 4 |
| Premium of 49-9041 over 49-9043: z of the change from 2021 / from 2022 | −5.1 / −0.2 |
| Premium over 51-9161 (CNC operators): z from 2021 / from 2022 | −2.2 / −0.8 |
| Close pool (51-9161, 51-4081, 51-4041): change from 2021 / from 2022 | −22.9% / −18.0% |

## 18. The 49-1011 Sensitivity (DL-35)
`python -m src.robustness` → `outputs/robustness/family_plus_49_1011.csv`. 49-1011
meets the target rule's size and precision thresholds (2,700 jobs, RSE 1.5%) but is not in `targets_core`, and the
registration records no reason. Point P of every frame feeder on Skills and Knowledge against a family with 49-1011.00
added at its 3363 employment weight (0.090), the other weights rescaled, and 49-1011.00 removed from the reference set.

| Result | Skills | Knowledge |
|---|---|---|
| Three closest core feeders, registered → with 49-1011 | 51-9161 6.0 → 7.4; 51-4081 8.1 → 9.6; 51-4041 9.1 → 11.7 | 51-2090 9.4 → 9.3; 51-9161 16.2 → 16.0; 51-9061 22.5 → 22.1 |
| Production supervisors (51-1011, sensitivity occupation) | 11.6 → 9.4 | 15.2 → 14.3 |

## 19. Observed CPS Moves and the Headline Rule (DL-37, DL-40, DL-42)
`python -m src.cps_moves` → `outputs/cps_moves/`; cache `data/interim/cps_employed.npz`.
80 monthly files (January 2020 – September 2026; October 2025 not collected); 3,773,834 employed person records;
2,374,459 linked pairs (link rate 83.7–86.2% by year). Fixed-width positions identical in the 2020 and 2025 layouts.

| Quantity (manufacturing) | Estimate [95% bootstrap interval] | Events / base |
|---|---|---|
| Q1 production → maintenance, per month | 0.188% [0.158, 0.220] | 149 / 80,774 |
| Q1, same employer | 0.052% [0.037, 0.070] | 44 / 80,774 |
| Q2 share of maintenance entrants coming from production (destination) | 22.0% [18.0, 26.5] | 99 / 440 |
| Q2, same employer | 28.8% [20.8, 37.2] | 40 / 135 |
| Q2 without allocated codes / same employer | 31.5% [26.0, 37.6] / 42.9% [31.6, 54.5] | 88 / 274; 39 / 90 |
| Q3 rate ratio, machinists vs other production | 1.75 [0.79, 3.02] | 14 vs 122 |

**Headline rule (DL-42).** Wherever the README states a CPS quantity, the headline is the estimate without allocated
occupation or industry codes (check iv); the registered primary (all records) is shown beside it. Evidence
(`outputs/cps_moves/allocation_diagnostic.csv`): among pairs in manufacturing at t−1, those with an allocated code change
occupation in 68.81% of cases against 4.57% without; 166 of the 440 maintenance entrants have an allocated code.

| Quantity (manufacturing) | Headline: no allocated codes | Registered primary | Events / base (headline) |
|---|---|---|---|
| Q1 production → maintenance, per 10,000 a month | 14.5 [11.8, 17.2] | 18.8 [15.8, 22.0] | 111 / 78,193 |
| Q1, same employer, per 10,000 a month (annualized) | 4.9 [3.3, 6.6] (0.59%) | 5.2 [3.7, 7.0] (0.62%) | 40 / 78,193 |
| Q2 share of maintenance entrants from production | 31.5% [26.0, 37.6] | 22.0% [18.0, 26.5] | 88 / 274 |
| Q2, same employer | 42.9% [31.6, 54.5] | 28.8% [20.8, 37.2] | 39 / 90 |
| Q3 rate ratio, machinists vs other production | 1.48 [0.48, 2.92] | 1.75 [0.79, 3.02] | 9 vs 92 |

## 20. Origin of Maintenance Entrants, Scale Illustration and Where the Maintenance Occupations Work (DL-43, DL-45, DL-46)
**Origin of entrants (DL-43).** `python -m src.cps_moves` → `outputs/cps_moves/q2_origin_composition.csv`. Universe = the
Q2 destination universe: employed in both months, in M and manufacturing at t, in a non-M code at t−1.

| t−1 occupation | Headline (n = 274) | Registered (n = 440) | Same employer, headline (n = 90) |
|---|---|---|---|
| Production, manufacturing | 30.1% [24.3, 36.1] | 21.1% | 42.3% [31.0, 54.1] |
| Production, other industry | 1.5% | 0.9% | 0.5% |
| Other installation, maintenance and repair (incl. helpers) | 16.9% [12.1, 21.6] | 12.9% | not reportable |
| Construction and extraction | 7.7% | 9.0% | not reportable |
| Transportation and material moving | 8.0% | 10.1% | not reportable |
| Architecture and engineering | 11.1% [7.0, 15.6] | 7.4% | not reportable |
| All other occupations | 24.7% [19.3, 30.8] | 38.5% | 23.7% [14.3, 34.3] |

'Not reportable' = NCHS relative interval width above 130%. Entrants from unemployment or from outside the labour force
are not in this universe (see A3).

**Scale illustration (DL-45).** `outputs/cps_moves/scale_illustration.csv`. Annualized same-employer rate 0.59% (headline;
0.40–0.79%) × OEWS May 2025 NAICS 336300 production employment (SOC 51-0000, 331,270) ≈ 1,950 a year (1,320–2,610);
registered primary ≈ 2,070. Beside it: illustrative annual separations of the maintenance family ≈ 2,146 (labour-force
exits ≈ 981; DL-13). Assumes the NAICS 3363 rate equals the manufacturing-wide rate and a constant monthly rate; not a
headline and not an estimate of 3363 flows.

**Where the M occupations work (DL-46).** `outputs/cps_moves/m_codes_by_sector.csv`: national employment of each M-code
SOC by NAICS sector (OEWS May 2025, sum of sector rows) and its share in manufacturing. Q1 'any employer' counts moves into
M codes in every industry, so the same-employer rate is the closer measure of in-plant succession.

| SOC | Sum of sector rows | Manufacturing (31–33) | Share | Largest sector |
|---|---|---|---|---|
| 47-2111 Electricians | 757,220 | 52,590 | 6.9% | Construction (599,700) |
| 49-9041 Industrial machinery mechanics | 438,040 | 232,500 | 53.1% | Manufacturing |
| 49-9043 Maintenance workers, machinery | 60,000 | 32,470 | 54.1% | Manufacturing |
| 49-9044 Millwrights | 40,060 | 14,590 | 36.4% | Construction (17,640) |
| 49-9045 Refractory materials repairers | 1,080 | 560 | 51.9% | Manufacturing |
| 49-9071 Maintenance and repair workers, general | 1,529,700 | 206,760 | 13.5% | Real estate and rental and leasing (323,560) |

One sector row is withheld for 49-9041 and one for 49-9044 (counted as zero in the sum).

The age profile and flows of DL-44 (A1–A3) run in II-A.

## 21. Repository Split: Mapping Tables (DL-36, DL-47, DL-48)
The single repository was split on 2026-10-29. Every output kept here equals the single-repository output (exact for
counts and text, within 1e-12 for floats; summaries apart from run times and the sections that moved to II-A).

**Figures**

| Single repository | II-B |
|---|---|
| fig1_h1_proximity_skills | fig1_h1_proximity_skills |
| fig14_cps_moves | fig2_cps_moves |
| fig4_proximity_vs_pool | fig3_proximity_vs_pool |
| fig5_skill_gap_heatmap | fig4_skill_gap_heatmap |
| fig2_h2_concentration_skills | fig5_h2_concentration_skills |
| fig7_osha_pathway | fig6_osha_pathway |
| fig3_multiverse | fig7_multiverse |
| fig8_uncertainty_models | fig8_uncertainty_models |
| figS1_abilities_negative_control | figS1_abilities_negative_control |
| fig6, fig9–fig13, fig15 | II-A |

**Audit checks**

| Single repository | II-B | Change |
|---|---|---|
| E1–E18 | E1–E18 | E13 lists the II-B figures |
| E20 | E19 | — |
| E24 | E20 | H1 and the premium z over the close feeders; the skill-shift, 49-9043 premium and floor-map parts run in II-A |
| E27 | E21 | — |
| E30 | E22 | — |
| E31 | E23 | — |
| E19 | E24 | baseline and adjustments only; the automation counts run in II-A (DL-48) |
| E21, E22, E23, E25, E26, E28, E29, E32 | II-A | — |

**Outputs removed here (they run in II-A):** `outputs/practice/industry_output.csv`,
`bls_adjustment_by_occupation_job_zone.csv`, `bls_adjustment_by_job_zone.csv` and the automation sections of
`practice_summary.md`; `outputs/skill_shift/`, `outputs/floor_map/`, `outputs/track_record/`, `outputs/cps_flows/`.

---
