# Data audit summary

Generated: 2026-10-30 02:03 UTC  
Pre-registration: v0.3 (frozen)  
O*NET release: 31.0

## 1. Ingested files

| file_key | file | domain | sha256 | rows | occupations | elements | n_problems | onet_release |
|---|---|---|---|---|---|---|---|---|
| knowledge | knowledge.csv | K | 88092e17d16096cd… | 60060 | 910 | 33 | 0 | 31.0 |
| abilities | abilities.csv | A | 7e9cd79791ce6014… | 94640 | 910 | 52 | 0 | 31.0 |
| essential_skills | essential_skills.csv | S | 68c4d31d8c550772… | 18200 | 910 | 10 | 0 | 31.0 |
| transferable_skills | transferable_skills.csv | S | f17d0419e818a3bf… | 45500 | 910 | 25 | 0 | 31.0 |

## 2. Reference universe

| domain | occupations | elements | rows | occupations_with_missing_se | expected_elements |
|---|---|---|---|---|---|
| A | 910 | 52 | 94640 | 0 | 52 |
| K | 910 | 33 | 60060 | 257 | 33 |
| S | 910 | 35 | 63700 | 0 | 35 |


Rating sources by domain (number of occupations):


| domain | domain_source | occupations |
|---|---|---|
| A | Analyst | 910 |
| K | Analyst - Transition | 9 |
| K | Incumbent | 653 |
| K | Occupational Expert | 248 |
| S | Analyst | 910 |

## 3. Crosswalk issues

None — every frame code was found.


Multi-code mappings:


| soc6 | onet_code | title | aggregation |
|---|---|---|---|
| 51-2028 | 51-2022.00 | Electrical and Electronic Equipment Assemblers | equal_weight_profile_mean |
| 51-2028 | 51-2023.00 | Electromechanical Equipment Assemblers | equal_weight_profile_mean |

## 4. Stop rule (pre-registered)

| domain | codes_in_scope | rows_in_scope | rows_flag_known | rows_flag_missing | suppress_Y | suppress_rate | max_rate | decision |
|---|---|---|---|---|---|---|---|---|
| A | 19 | 1976 | 1976 | 0 | 1 | 0.001 | 0.200 | PASS |
| K | 19 | 1254 | 1188 | 66 | 189 | 0.159 | 0.200 | PASS |
| S | 19 | 1330 | 1330 | 0 | 1 | 0.001 | 0.200 | PASS |

## 5. Codes needing SE imputation

| soc6 | role | onet_code | mapping_type | domain | se_missing_rate | domain_sources | n_median | primary_handling | sensitivity_handling |
|---|---|---|---|---|---|---|---|---|---|
| 49-9044 | target_core | 49-9044.00 | primary | K | 1.000 | Occupational Expert | 22.000 | impute_median_se_incumbent_by_element_scale | drop_frame_codes_without_se_from_domain |
| 17-3024 | target_sensitivity | 17-3024.01 | sensitivity | K | 1.000 | Occupational Expert | 22.000 | impute_median_se_incumbent_by_element_scale | drop_frame_codes_without_se_from_domain |

## 6. Rating collection years (primary mappings)

Range across frame codes: 2014–2026.


## 7. Frame audit (primary mappings)

| soc6 | role | onet_code | domain | coverage | suppress_rate | se_missing_rate | n_median | year_min | domain_sources |
|---|---|---|---|---|---|---|---|---|---|
| 49-9041 | target_core | 49-9041.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 49-9041 | target_core | 49-9041.00 | K | 1.000 | 0.182 | 0.000 | 21.000 | 2021 | Incumbent |
| 49-9041 | target_core | 49-9041.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 49-9071 | target_core | 49-9071.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 49-9071 | target_core | 49-9071.00 | K | 1.000 | 0.106 | 0.000 | 58.000 | 2021 | Incumbent |
| 49-9071 | target_core | 49-9071.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 47-2111 | target_core | 47-2111.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2022 | Analyst |
| 47-2111 | target_core | 47-2111.00 | K | 1.000 | 0.121 | 0.000 | 20.000 | 2022 | Incumbent |
| 47-2111 | target_core | 47-2111.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2022 | Analyst |
| 49-9043 | target_core | 49-9043.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2024 | Analyst |
| 49-9043 | target_core | 49-9043.00 | K | 1.000 | 0.136 | 0.000 | 18.000 | 2024 | Incumbent |
| 49-9043 | target_core | 49-9043.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2024 | Analyst |
| 49-9044 | target_core | 49-9044.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2024 | Analyst |
| 49-9044 | target_core | 49-9044.00 | K | 1.000 |  | 1.000 | 22.000 | 2024 | Occupational Expert |
| 49-9044 | target_core | 49-9044.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2024 | Analyst |
| 49-2094 | target_sensitivity | 49-2094.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 49-2094 | target_sensitivity | 49-2094.00 | K | 1.000 | 0.076 | 0.000 | 20.000 | 2021 | Incumbent |
| 49-2094 | target_sensitivity | 49-2094.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 17-3024 | target_sensitivity | 17-3024.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2022 | Analyst |
| 17-3024 | target_sensitivity | 17-3024.00 | K | 1.000 | 0.076 | 0.000 | 38.000 | 2022 | Incumbent |
| 17-3024 | target_sensitivity | 17-3024.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2022 | Analyst |
| 51-2090 | feeder_core | 51-2092.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2020 | Analyst |
| 51-2090 | feeder_core | 51-2092.00 | K | 1.000 | 0.076 | 0.000 | 26.000 | 2020 | Incumbent |
| 51-2090 | feeder_core | 51-2092.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2020 | Analyst |
| 51-4031 | feeder_core | 51-4031.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2025 | Analyst |
| 51-4031 | feeder_core | 51-4031.00 | K | 1.000 | 0.333 | 0.000 | 17.000 | 2025 | Incumbent |
| 51-4031 | feeder_core | 51-4031.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2025 | Analyst |
| 51-2031 | feeder_core | 51-2031.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2014 | Analyst |
| 51-2031 | feeder_core | 51-2031.00 | K | 1.000 | 0.136 | 0.000 | 32.000 | 2014 | Incumbent |
| 51-2031 | feeder_core | 51-2031.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2014 | Analyst |
| 51-9061 | feeder_core | 51-9061.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2020 | Analyst |
| 51-9061 | feeder_core | 51-9061.00 | K | 1.000 | 0.091 | 0.000 | 20.000 | 2020 | Incumbent |
| 51-9061 | feeder_core | 51-9061.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2020 | Analyst |
| 51-4121 | feeder_core | 51-4121.00 | A | 1.000 | 0.010 | 0.000 | 8.000 | 2022 | Analyst |
| 51-4121 | feeder_core | 51-4121.00 | K | 1.000 | 0.121 | 0.000 | 41.000 | 2022 | Incumbent |
| 51-4121 | feeder_core | 51-4121.00 | S | 1.000 | 0.014 | 0.000 | 8.000 | 2022 | Analyst |
| 51-4081 | feeder_core | 51-4081.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 51-4081 | feeder_core | 51-4081.00 | K | 1.000 | 0.121 | 0.000 | 18.000 | 2021 | Incumbent |
| 51-4081 | feeder_core | 51-4081.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 51-4041 | feeder_core | 51-4041.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2020 | Analyst |
| 51-4041 | feeder_core | 51-4041.00 | K | 1.000 | 0.242 | 0.000 | 27.000 | 2020 | Incumbent |
| 51-4041 | feeder_core | 51-4041.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2020 | Analyst |
| 51-2028 | feeder_core | 51-2022.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2026 | Analyst |
| 51-2028 | feeder_core | 51-2022.00 | K | 1.000 | 0.212 | 0.000 | 18.000 | 2026 | Incumbent |
| 51-2028 | feeder_core | 51-2022.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2026 | Analyst |
| 51-2028 | feeder_core | 51-2023.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2017 | Analyst |
| 51-2028 | feeder_core | 51-2023.00 | K | 1.000 | 0.242 | 0.000 | 24.000 | 2017 | Incumbent |
| 51-2028 | feeder_core | 51-2023.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2017 | Analyst |
| 51-9161 | feeder_core | 51-9161.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2023 | Analyst |
| 51-9161 | feeder_core | 51-9161.00 | K | 1.000 | 0.061 | 0.000 | 38.000 | 2023 | Incumbent |
| 51-9161 | feeder_core | 51-9161.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2023 | Analyst |
| 51-4072 | feeder_core | 51-4072.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2016 | Analyst |
| 51-4072 | feeder_core | 51-4072.00 | K | 1.000 | 0.152 | 0.000 | 35.000 | 2016 | Incumbent |
| 51-4072 | feeder_core | 51-4072.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2016 | Analyst |
| 51-4122 | feeder_core | 51-4122.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2024 | Analyst |
| 51-4122 | feeder_core | 51-4122.00 | K | 1.000 | 0.152 | 0.000 | 18.000 | 2024 | Incumbent |
| 51-4122 | feeder_core | 51-4122.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2024 | Analyst |
| 51-9124 | feeder_core | 51-9124.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2022 | Analyst |
| 51-9124 | feeder_core | 51-9124.00 | K | 1.000 | 0.288 | 0.000 | 39.000 | 2022 | Incumbent |
| 51-9124 | feeder_core | 51-9124.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2022 | Analyst |
| 51-1011 | sensitivity | 51-1011.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2020 | Analyst |
| 51-1011 | sensitivity | 51-1011.00 | K | 1.000 | 0.015 | 0.000 | 36.000 | 2020 | Incumbent |
| 51-1011 | sensitivity | 51-1011.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2020 | Analyst |
| 51-4111 | sensitivity | 51-4111.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 51-4111 | sensitivity | 51-4111.00 | K | 1.000 | 0.167 | 0.000 | 18.000 | 2021 | Incumbent |
| 51-4111 | sensitivity | 51-4111.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2021 | Analyst |
| 17-3026 | sensitivity | 17-3026.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2026 | Analyst |
| 17-3026 | sensitivity | 17-3026.00 | K | 1.000 | 0.076 | 0.000 | 18.000 | 2026 | Incumbent |
| 17-3026 | sensitivity | 17-3026.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2026 | Analyst |
| 53-7062 | negative_control | 53-7062.00 | A | 1.000 | 0.000 | 0.000 | 8.000 | 2024 | Analyst |
| 53-7062 | negative_control | 53-7062.00 | K | 1.000 | 0.091 | 0.000 | 27.000 | 2024 | Incumbent |
| 53-7062 | negative_control | 53-7062.00 | S | 1.000 | 0.000 | 0.000 | 8.000 | 2024 | Analyst |

## 8. Reviewer checklist

- [ ] All primary codes resolved (Section 3 first table empty)
- [ ] Coverage = 1.000 for every primary code x domain
- [ ] Stop rule decision recorded for each domain
- [ ] SE-imputation cases match prereg measurement.missing_se
- [ ] Collection-year spread noted for the limitations section
- [ ] Any deviation logged in outputs/deviation_log.md before analysis begins
