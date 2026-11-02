# Data integrity review

Status: PASS = verified; NOTE = true, must be disclosed; FLAG = needs a decision.


## A

- **A1 [PASS] Rating values inside published scale ranges (LV 0–7, IM 1–5)** — 0 out-of-range rows of 218,400
- **A2 [PASS] Published 95% CI consistent with SE** — half-width / SE: median 1.96 (IQR 1.96–1.96); value inside its CI in 100.0% of 159,335 rows. Ratios above 1.96 are consistent with small-sample t intervals; the bootstrap uses SE directly.
- **A3 [PASS] 'Not Relevant' flag behaves as documented (low importance)** — median Importance when flagged 1.00 vs not flagged 2.75; median Level when flagged 0.00 (17,169 flagged Level rows). Primary spec uses Level as published; the 'zero' multiverse branch sets these to 0.
- **A4 [PASS] 'Recommend Suppress' marks low-precision ratings** — median SE flagged 0.292 vs unflagged 0.164
- **A5 [PASS] Skills union has no element shared by the two Skills files** — overlap: none
- **A6 [PASS] OEWS 3363 detailed rows reconcile with the industry total** — detailed employment sums to 99.7% of total (2 detailed rows withheld '**'); max |TOT_EMP/total − PCT_TOTAL| = 0.0056 pp
- **A7 [PASS] EP Table 1.10 identity: openings = separations + employment change / 10** — max abs deviation 0.10k, 99th pct 0.09k over 831 line items (rounding in published thousands)

## B

- **B1 [PASS] Classification systems linked by the BLS crosswalk** — O*NET-SOC 2019 ↔ NEM 2025 ↔ SOC 2018 (OEWS) verified code by code in outputs/validation/ep_crosswalk_check.csv (23/23 OK)
- **B2 [NOTE] Rating vintage vs. 2025 employment data** — frame ratings collected 2014–2026; before 2018: 51-2031.00 (2014), 51-4072.00 (2016), 51-2023.00 (2017). O*NET dates are occupation-level update dates shared by K/S/A, so vintage cannot be separated from occupation.
- **B3 [NOTE] Industry scope differs by source** — OEWS weights are NAICS 3363-specific; O*NET ratings and EP projections are all-industry national. KSA profiles therefore describe each occupation economy-wide, not inside auto-parts plants.

## C

- **C1 [NOTE] Knowledge rater source is mixed; one core target is expert-rated** — mean K Level by source: Analyst - Transition 2.34, Incumbent 2.00, Occupational Expert 2.47. Millwrights K source: ['Occupational Expert']. Correlation of Millwrights' K profile with other core targets 0.75 vs mean among the other four 0.67.
- **C2 [NOTE] Family target weights are concentrated** — π: 49-9041 48.3%, 49-9071 29.9%, 47-2111 10.7%, 49-9043 6.2%, 49-9044 4.9%. 49-9041 + 49-9071 = 78.2%; equal weights are the registered sensitivity.
- **C3 [NOTE] Feeder employment dominated by a proxy-mapped code** — 51-2090 (proxied by Team Assemblers) = 47.4% of core feeder employment. Matters only for employment-weighted summaries; per-feeder estimates are unaffected.
- **C4 [NOTE] 51-2028 profile mean combines two vintages (2026 and 2017)** — Level-profile correlation between the two codes: K 0.84, S 0.69, A 0.96
- **C5 [NOTE] Knowledge deficit rewards broadly high-knowledge occupations** — Directional D gives zero or near-zero deficit to occupations at or above the family on every element, e.g. Construction Managers; Heating, Air Conditioning, and Refrigeration Mechanics and Installers; Biofuels Production Managers; Agricultural Engineers; Industrial Engineers. K proximity therefore means 'lacks little', not 'is similar'. S and A nearest neighbours are maintenance/technical occupations.
- **C6 [FLAG] Pre-registered negative control** — A: P=40.7 (FAIL); K: P=67.6 (PASS); S: P=94.6 (PASS). A-domain failure: hand laborers share the physical abilities that maintenance work requires.

## D

- **D1 [NOTE] Shape of the C–D relation in the reference universe** — A: R² linear 0.48, log 0.71; mean linear residual by D-quintile +0.030/-0.028/-0.026/+0.001/+0.024 | K: R² linear 0.44, log 0.37; mean linear residual by D-quintile +0.011/-0.025/+0.003/+0.013/-0.002 | S: R² linear 0.26, log 0.20; mean linear residual by D-quintile -0.035/+0.017/+0.016/+0.035/-0.032
- **D2 [NOTE] POST-HOC (DL-7): D-matched local percentile of feeder concentration** — median local percentile / feeders below 10th pct (of 12): A 10.5 / 5.0, K 8.5 / 6.0, S 12.5 / 4.0. Exploratory; does not replace the registered test.
