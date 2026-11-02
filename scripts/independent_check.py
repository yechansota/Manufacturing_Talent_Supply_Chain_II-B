"""Independent re-implementation (output audit E16, DL-25d) of the core estimands from the RAW files only.

Does not import any project module and does not read the DuckDB store. Reads:
  data/raw/onet/{knowledge,essential_skills,transferable_skills,abilities}.csv
  data/raw/oews/oesm25in4.zip (nat4d_M2025_dl.xlsx, NAICS 336300)
Recomputes, for the FAMILY target in each domain: D, P, C(top 5), and the family weights pi,
then compares with outputs/estimates/point_pairs.csv. Also re-derives wage medians and the
employment figures quoted in the README.
"""
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parents[1]
raw = R / "data/raw"

TARGETS = ["49-9041", "49-9071", "47-2111", "49-9043", "49-9044"]
FEEDERS = {"51-2090": ["51-2092.00"], "51-4031": ["51-4031.00"], "51-2031": ["51-2031.00"], "51-9061": ["51-9061.00"],
           "51-4121": ["51-4121.00"], "51-4081": ["51-4081.00"], "51-4041": ["51-4041.00"],
           "51-2028": ["51-2022.00", "51-2023.00"], "51-9161": ["51-9161.00"], "51-4072": ["51-4072.00"],
           "51-4122": ["51-4122.00"], "51-9124": ["51-9124.00"], "51-1011": ["51-1011.00"], "51-4111": ["51-4111.00"],
           "17-3026": ["17-3026.00"], "53-7062": ["53-7062.00"]}

# ---- OEWS, read directly from the zip
with zipfile.ZipFile(raw / "oews/oesm25in4.zip") as z:
    with z.open("oesm25in4/nat4d_M2025_dl.xlsx") as fh:
        o = pd.read_excel(fh, dtype=str)
o = o[o.NAICS.astype(str).str.strip() == "336300"]
num = lambda s: pd.to_numeric(s.str.replace(",", "", regex=False), errors="coerce")
o["emp"] = num(o.TOT_EMP); o["hmed"] = num(o.H_MEDIAN)
emp = o.drop_duplicates("OCC_CODE").set_index("OCC_CODE")
total = float(emp.loc["00-0000", "emp"])
pi = emp.loc[TARGETS, "emp"] / emp.loc[TARGETS, "emp"].sum()

# ---- O*NET, read directly
files = {"K": ["knowledge.csv"], "S": ["essential_skills.csv", "transferable_skills.csv"], "A": ["abilities.csv"]}
pp = pd.read_csv(R / "outputs/estimates/point_pairs.csv")
pp = pp[pp.target == "FAMILY"].set_index(["domain", "feeder"])
rows, worst = [], 0.0
for d, fl in files.items():
    r = pd.concat([pd.read_csv(raw / "onet" / f, dtype={"Data Value": float}) for f in fl])
    L = r[r["Scale ID"] == "LV"].pivot_table(index="O*NET-SOC Code", columns="Element ID", values="Data Value", aggfunc="first")
    I = r[r["Scale ID"] == "IM"].pivot_table(index="O*NET-SOC Code", columns="Element ID", values="Data Value", aggfunc="first")
    keep = L.dropna().index.intersection(I.dropna().index)
    L, I = L.loc[keep].sort_index(), I.loc[keep, L.columns].sort_index()
    Z = (L - L.mean()) / L.std(ddof=1)
    W = I - 1.0
    tcodes = [t + ".00" for t in TARGETS]
    z_t = sum(pi[t] * Z.loc[t + ".00"] for t in TARGETS)
    w_t = sum(pi[t] * W.loc[t + ".00"] for t in TARGETS)
    ref = Z.drop(index=tcodes)
    c_ref = (ref.rsub(z_t, axis=1)).clip(lower=0) * w_t
    D_ref = c_ref.sum(axis=1) / w_t.sum()
    for f, codes in FEEDERS.items():
        zf = Z.loc[codes].mean()
        c = (z_t - zf).clip(lower=0) * w_t
        D = c.sum() / w_t.sum()
        P = 100 * float((D_ref <= D + 1e-12).mean())
        C = float(np.sort(c.to_numpy())[::-1][:5].sum() / c.sum())
        reg = pp.loc[(d, f)]
        dev = max(abs(D - reg.D), abs(P - reg.P), abs(C - reg.C_top))
        worst = max(worst, dev)
        rows.append({"domain": d, "feeder": f, "D": D, "D_reg": reg.D, "P": P, "P_reg": reg.P, "C": C, "C_reg": reg.C_top, "max_dev": dev})
    print(f"{d}: {len(keep)} occupations, {L.shape[1]} elements, reference {len(ref)}")
df = pd.DataFrame(rows)
print(df.round(4).to_string(index=False))
print(f"\nmax |independent - registered| over D, P, C: {worst:.2e}")
print("pi:", pi.round(4).to_dict(), "OEWS 3363 total:", total)
fam_wage = float((pi * emp.loc[TARGETS, "hmed"]).sum())
print("family median wage approx:", round(fam_wage, 2))
print("close pool:", emp.loc[["51-9161", "51-4081", "51-4041"], "emp"].sum(), "family:", emp.loc[TARGETS, "emp"].sum())
sys.exit(0 if worst < 1e-9 else 1)
