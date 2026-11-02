# Data Download Guide (II-B)

Every input is a free public file; no login is needed. This guide lists each file, where to get it, the exact name and
folder it must have, and how to check it. Allow about an hour: the 80 CPS monthly zips are about 800 MB in total.

> The pre-registration is **frozen** with the eight registered files of sections 1–3 (`outputs/freeze_record.md`). If a
> re-downloaded registered file differs from the SHA-256 recorded at the freeze, `python scripts/freeze.py --verify`
> fails and the pipeline stops.

---

## 0. Folder layout

Put the files in these folders inside the repository. Folder names are lower case, exactly as shown.

```
data/raw/
├── onet/          knowledge.csv, abilities.csv, essential_skills.csv, transferable_skills.csv   (registered)
│                  training_and_experience.csv, training_and_experience_categories.csv,
│                  job_zones.csv, job_zone_reference.csv
├── oews/          oesm25in4.zip                                                                  (registered)
├── oews_history/  oesm21in4.zip, oesm22in4.zip, oesm23in4.zip, oesm24in4.zip
├── ep/            occupation.xlsx, education.xlsx, nem-onet-to-soc-crosswalk.xlsx               (registered)
│                  National_Employment_Matrix_IND_336300.csv
├── ces/           one BLS export of series CEU3133630001 from 2016
├── cps/basic/     jan20pub.zip … sep26pub.zip  (80 files)
├── cps/docs/      record layouts and the Census note on linking (reference only)
└── census_codes/  2018-occupation-code-list-and-crosswalk.xlsx,
                   2017-industry-code-list-with-crosswalk.xlsx,
                   2022-Census-Industry-Code-List-with-Crosswalk.xlsx
```

## Rules

1. **Use the exact file names above.** Browsers sometimes add ` (1)` or `_1` to a name (for example
   `knowledge_1.csv`); delete only the added part.
2. **Do not save a CSV or XLSX after opening it in Excel.** Excel can change codes, dates and encoding. If you saved one
   by mistake, delete it and download it again.
3. **Leave every `.zip` file zipped.** The code reads the zips directly (OEWS, CPS).
4. **Do not substitute another release.** The registered files are frozen; the code checks their release and stops on a
   mismatch.

---

## 1. O*NET 31.0 → `data/raw/onet/`

**Registered (4 files).** Click each link; the file downloads directly.

| File | Content | Link |
|---|---|---|
| `knowledge.csv` | Knowledge (33 elements) | https://www.onetcenter.org/dl_files/database/db_31_0_csv/knowledge.csv |
| `abilities.csv` | Abilities (52 elements) | https://www.onetcenter.org/dl_files/database/db_31_0_csv/abilities.csv |
| `essential_skills.csv` | Essential skills (10 elements) | https://www.onetcenter.org/dl_files/database/db_31_0_csv/essential_skills.csv |
| `transferable_skills.csv` | Transferable skills (25 elements) | https://www.onetcenter.org/dl_files/database/db_31_0_csv/transferable_skills.csv |

**Training layer (4 files, DL-21).** They come in the full release zip
https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip — unzip it and copy only these files (rename them to the
names below if they differ). The pipeline stops at the practice layer if one of the first three is missing.

| File | Content | Rows (excluding header) |
|---|---|---|
| `training_and_experience.csv` | response shares by category: related work experience (RW), on-site training (PT), on-the-job training (OJ) | 26,812 |
| `training_and_experience_categories.csv` | category descriptions (for example "Over 1 year, up to and including 2 years") | 29 |
| `job_zones.csv` | Job Zone of each occupation (release 31.0 merges zones 1 and 2 into "1-2") | 923 |
| `job_zone_reference.csv` | Job Zone descriptions; reference only, not read by the code | 4 |

**If a link shows text on screen instead of downloading:** press `Ctrl + S` (`Cmd + S` on a Mac), choose "All files",
check the name ends in `.csv`, and save.

**If the 31.0 links no longer work:** get release **31.0** from the archived releases page
(https://www.onetcenter.org/db_releases.html). Do not use another release.

**Check:** rows excluding the header — knowledge 60,060; abilities 94,640; essential_skills 18,200; transferable_skills
45,500 (checked by the code).

---

## 2. OEWS, NAICS 336300

**May 2025 → `data/raw/oews/` (registered)**

| File | Link |
|---|---|
| `oesm25in4.zip` | https://www.bls.gov/oes/special-requests/oesm25in4.zip |

**May 2021–2024 → `data/raw/oews_history/` (maintenance family and close-feeder pool over time, DL-29)**

| File | Link |
|---|---|
| `oesm21in4.zip` | https://www.bls.gov/oes/special-requests/oesm21in4.zip |
| `oesm22in4.zip` | https://www.bls.gov/oes/special-requests/oesm22in4.zip |
| `oesm23in4.zip` | https://www.bls.gov/oes/special-requests/oesm23in4.zip |
| `oesm24in4.zip` | https://www.bls.gov/oes/special-requests/oesm24in4.zip |

These are the "National industry-specific and by ownership" files on https://www.bls.gov/oes/tables.htm. Each zip holds
every industry; the code keeps NAICS 336300. The history files go in their own folder so they never mix with the
registered May 2025 file. BLS does not encourage comparing OEWS estimates over time
([OEWS FAQ](https://www.bls.gov/oes/oes_ques.htm)); the README reads the changes as observed differences.

**Check:** `oesm25in4.zip` must contain `oesm25in4/nat4d_M2025_dl.xlsx`; the NAICS 336300 total must be 538,980 jobs
(checked by the code).

---

## 3. BLS Employment Projections 2025–35 → `data/raw/ep/`

| File | Where to get it |
|---|---|
| `occupation.xlsx` (registered) | https://www.bls.gov/emp/tables.htm → "Occupations" → **All occupational tables in a single file (XLSX)** |
| `education.xlsx` (registered) | same page → "Education and Training" → **All education tables in a single file (XLSX)** |
| `nem-onet-to-soc-crosswalk.xlsx` (registered) | https://www.bls.gov/emp/data/occupational-data.htm → **O*NET-SOC to National Employment Matrix/Occupational Outlook Handbook Crosswalk (XLSX)** |
| `National_Employment_Matrix_IND_336300.csv` (DL-23) | see below |

**National Employment Matrix for NAICS 336300** (projections inside the industry; the step is skipped if the file is
absent):
1. Open https://data.bls.gov/projections/nationalMatrix?queryParams=336300&ioType=i
2. Use the export button above the table and choose **CSV**.
3. Check the name is `National_Employment_Matrix_IND_336300.csv`. Codes appear as `="00-0000"`; leave them as they are.

**Check:** the Table 1.10 sheet title of `occupation.xlsx` contains "2025–35" and the crosswalk shows "As of 08/27/2026"
(both checked by the code). The first row of the matrix CSV is `Total, all occupations`.

---

## 4. BLS Current Employment Statistics, series CEU3133630001 → `data/raw/ces/` (DL-26)

All employees in motor vehicle parts manufacturing (NAICS 3363), not seasonally adjusted, thousands. The step is
skipped if the file is absent.

1. Open https://data.bls.gov/timeseries/CEU3133630001
2. Set the years from **2016** to the latest year and download the table as **XLSX**.
3. Keep the file name BLS gives (for example `SeriesReport-….xlsx`). Put only this one file in the folder.

A FRED CSV of the same series (`observation_date,CEU3133630001`) is also read, but this repository used the BLS file.
**Check:** the top of the file shows `Series Id: CEU3133630001` and `Not Seasonally Adjusted`. BLS revises CES estimates
in the following months and at each annual benchmark
([BLS, CES benchmark article](https://www.bls.gov/web/empsit/cesbmart.htm)), so a later download can differ.

---

## 5. CPS basic monthly public-use files → `data/raw/cps/` (DL-37)

Used for the observed production → maintenance moves (manufacturing as a whole). The step is skipped if the files are
absent.

**Data (`cps/basic/`):** every month from January 2020 to the latest month, in the DOS/Windows `.zip` format.
- Yearly pages: https://www.census.gov/data/datasets/time-series/demo/cps/cps-basic.html → choose the year.
- File address pattern: `https://www2.census.gov/programs-surveys/cps/datasets/<YEAR>/basic/<mon><yy>pub.zip`, for
  example https://www2.census.gov/programs-surveys/cps/datasets/2020/basic/jan20pub.zip
- Names: three-letter month in lower case + two-digit year + `pub.zip` (`jan20pub.zip` … `sep26pub.zip`).
- **October 2025 does not exist:** "CPS data were not collected for October 2025 due to the lapse in appropriations",
  and there is no public-use file for that month
  ([BLS](https://www.bls.gov/cps/methods/2025-federal-government-shutdown-impact-cps.htm)). January 2020 – September
  2026 therefore gives 80 files.
- Do not unzip. Each zip holds one fixed-width `.dat` file of 1,000-character records.

**Documentation (`cps/docs/`, reference only; the code does not read it):**

| Saved here as | Official file | Link |
|---|---|---|
| `Basic_CPS_Record_Layout_starting_2020.txt` | `2020_Basic_CPS_Public_Use_Record_Layout_plus_IO_Code_list.txt` | https://www2.census.gov/programs-surveys/cps/datasets/2020/basic/2020_Basic_CPS_Public_Use_Record_Layout_plus_IO_Code_list.txt |
| `Basic_CPS_Record_Layout_starting_2025.txt` | `2025_Basic_CPS_Public_Use_Record_Layout_plus_IO_Code_list.txt` | https://www2.census.gov/programs-surveys/cps/datasets/2025/basic/2025_Basic_CPS_Public_Use_Record_Layout_plus_IO_Code_list.txt |
| `How_To_Link_CPS_Public_Use_Files.pdf` | same | https://www2.census.gov/programs-surveys/cps/methodology/How_To_Link_CPS_Public_Use_Files.pdf |

The field positions the code uses are identical in the 2020 and 2025 layouts.

---

## 6. Census industry and occupation code lists → `data/raw/census_codes/` (DL-40)

Source page: https://www.census.gov/topics/employment/industry-occupation/guidance/code-lists.html

| File | Link |
|---|---|
| `2018-occupation-code-list-and-crosswalk.xlsx` | https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-occupation-code-list-and-crosswalk.xlsx |
| `2017-industry-code-list-with-crosswalk.xlsx` | https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2017-industry-code-list-with-crosswalk.xlsx |
| `2022-Census-Industry-Code-List-with-Crosswalk.xlsx` | https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2022-Census-Industry-Code-List-with-Crosswalk.xlsx |

They map CPS occupation and industry codes to SOC and NAICS. The code checks that the maintenance and machinist codes map
to the expected SOC codes and that industry 3570 is in manufacturing.

---

## 7. Versions used in this repository

| Input | Version |
|---|---|
| O*NET | release 31.0 |
| OEWS | May 2021–2025 (national industry-specific); May 2025 registered |
| BLS Employment Projections | 2025–35; crosswalk "As of 08/27/2026" |
| CES CEU3133630001 | export of 2026-10-19 (2016 onward), as stamped in the BLS file name |
| CPS basic monthly | January 2020 – September 2026 (80 files) |
| Census code lists | 2018 occupation; 2017 and 2022 industry |

`outputs/freeze_record.md` records the SHA-256 of the eight registered files; `data/raw/MANIFEST.csv` records the
SHA-256 of every file used. Compare yours with them to see whether a file differs.

## 8. Check the files

From the repository root:

```bash
python scripts/check_downloads.py      # PASS / MISSING for the registered files; writes data/raw/MANIFEST.csv (SHA-256)
python scripts/freeze.py --verify      # registered files and prereg.yaml match the freeze record
```

## Common problems

| Symptom | Fix |
|---|---|
| A link shows numbers and text on screen | save with `Ctrl/Cmd + S` (section 1) |
| A BLS page is slow or refuses the connection | try again a few minutes later or in another browser |
| A name changed to `knowledge (1).csv` / `knowledge_1.csv` | delete the added part |
| A file was saved after opening it in Excel | delete it and download it again |
| A CPS zip cannot be opened (`BadZipFile`) or a month fails to parse | the download is damaged; download that month again |
| `freeze.py --verify` reports a changed raw file | the source may have updated the file; stop, record it in `outputs/deviation_log.md`, and decide before going on |
