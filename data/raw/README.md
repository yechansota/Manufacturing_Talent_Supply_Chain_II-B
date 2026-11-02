# data/raw — immutable downloads (II-B)

Follow `docs/DATA_DOWNLOAD_GUIDE.md`. Never edit files here; re-download instead. Nothing in this folder is committed
except this README, `MANIFEST.csv` and the `.gitkeep` placeholders.

**Registered inputs** (in the freeze record; `python scripts/freeze.py --verify` checks them):

| Folder | Expected contents |
|---|---|
| `onet/` | `knowledge.csv`, `abilities.csv`, `essential_skills.csv`, `transferable_skills.csv` (O*NET 31.0, CSV) |
| `oews/` | `oesm25in4.zip` (OEWS May 2025 national industry-specific; leave zipped) |
| `ep/` | `occupation.xlsx`, `education.xlsx`, `nem-onet-to-soc-crosswalk.xlsx` (EP 2025–35) |

**Optional inputs** (added after the freeze; SHA-256 in `MANIFEST.csv`; each step is skipped with a note if absent):

| Folder | File | Used by | Log |
|---|---|---|---|
| `onet/` | `training_and_experience.csv`, `training_and_experience_categories.csv`, `job_zones.csv`, `job_zone_reference.csv` | training-time layer | DL-21 |
| `ep/` | `National_Employment_Matrix_IND_336300.csv` | projections inside NAICS 336300 (pathway table) | DL-23 |
| `ces/` | BLS CES export for series CEU3133630001 | observed industry employment | DL-26 |
| `oews_history/` | `oesm21in4.zip` … `oesm24in4.zip` (leave zipped) | maintenance family and close-feeder pool, 2021–2025 | DL-29, DL-36e |
| `cps/basic/` | `jan20pub.zip` … (CPS basic monthly public-use files, January 2020 onward) | observed production → maintenance moves | DL-37 |
| `cps/docs/` | record layouts (2020, 2025) and the Census note on linking | reference only | DL-37 |
| `census_codes/` | 2018 Census occupation code list; 2017 and 2022 Census industry code lists (with crosswalks) | CPS code groups | DL-40 |

`python scripts/check_downloads.py` regenerates `MANIFEST.csv`;
`python scripts/freeze.py --verify` compares the registered files with the freeze record.
