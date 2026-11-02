# Freeze record

Frozen at (UTC): 2026-10-18T19:11:28Z  
prereg.yaml SHA-256: `9fe627f24f8fbbaba15f0b6eaf577fedd3d0dee049db59005ad81b8d992904f7`

Any change to `config/prereg.yaml` after this point must be logged in `outputs/deviation_log.md` before the affected analysis is run. `python scripts/freeze.py --verify` checks the hashes below.

## Raw inputs (from data/raw/MANIFEST.csv)

| path | bytes | sha256 |
|---|---|---|
| data/raw/ep/education.xlsx | 118332 | `67b78dbccc8d6002e6c30f39a75d381380e2e9347bd2d87d71c3c98e7f36a531` |
| data/raw/ep/nem-onet-to-soc-crosswalk.xlsx | 94441 | `cf3c6e6cf1198f9896a0e280c7503f6cc2202be0660d5decff9c4562c78556e3` |
| data/raw/ep/occupation.xlsx | 413398 | `a7d060f0576f7d4f5b829b9a0bb4a6c11a12766d159ebb0e07aab5bd2e7583c5` |
| data/raw/oews/oesm25in4.zip | 31514940 | `3ef0e42fab1b42a7dac8a3a9b3e7024f5d7a07eff308bff5fc91808061ec08e1` |
| data/raw/onet/abilities.csv | 12667583 | `7e9cd79791ce6014e1d26d0a449ae5b1e7aa7ef52d39b3934c3bb8d438104b88` |
| data/raw/onet/essential_skills.csv | 2328135 | `68c4d31d8c55077238395dca40cc4e6d32e6a608b5474bb8264b1f98ae415bd7` |
| data/raw/onet/knowledge.csv | 8013560 | `88092e17d16096cdebe292fee4389deb460edda24ae8b4637212c69c71562f55` |
| data/raw/onet/transferable_skills.csv | 6081245 | `f17d0419e818a3bf2f55076510c76c4aef01cc8f5aee2670d2f44f6f44ac60f7` |

## Pre-analysis check outputs

| path | sha256 |
|---|---|
| outputs/audit/audit_crosswalk.csv | `cb4e1ed048f4c1a98ced12ec247da509853af285cd5e9af6988ca851ba87bfcc` |
| outputs/audit/audit_frame.csv | `f2c697b0041c61e79b61f657091f242b17b27d12adfb0d7c7d1472fb6b68eeea` |
| outputs/audit/audit_missing_se.csv | `1a23bd9ab32809ed6678472ec5fe0edc7b413db087744a823a4d7aeba84fff20` |
| outputs/audit/audit_stop_rule.csv | `33f0b8e15f374cf6183069e08016d9e7ae5ea3ae1acc8c02a56e62c5a1f7d342` |
| outputs/audit/audit_summary.md | `ee0990046a0a510cffbe8e05eb67197f7722e1b6bb6a476a9ec50ce52e25c4a4` |
| outputs/audit/audit_universe.csv | `ecdeb15dc30f06f78ef2725afba438a3bfd2fc6162f300d6649fe3041bceaed2` |
| outputs/validation/ep_crosswalk_check.csv | `644036104c995a44a889154f999855d45c579ebb93bd08ed3b6f3b7c86e79041` |
| outputs/validation/ep_frame_extract.csv | `2f5875f134256bf64708ff791a29854f679446f8aa3ae1cbc8077ace6c7d5486` |
| outputs/validation/oews_duplicate_codes.csv | `78e32c05045db051e163d35f35850aa343ba6de04dca0e7638d3bf372028708e` |
| outputs/validation/oews_feeders_threshold_alt.csv | `3f38b91031af4ac7c8bb4d411f8cc4273168bb7651fa4f5688f465859507d661` |
| outputs/validation/oews_frame_validation.csv | `a82b72bd3ac706019571004f8883d9be817a794c91ab4ac0f822cd713687e08a` |
