# Bootstrap results (primary specification)

Generated: 2026-10-30 02:06 UTC  
B = 1000, seed = 20261003, 123.9 s; SE imputed for 16962 K cells (prereg D2).  
Point-path consistency max deviation: 1.42e-14.  
Centering: A: median (boot mean D − point D) = -0.0036, max |.| = 0.0192 | K: median (boot mean D − point D) = +0.0288, max |.| = 0.0860 | S: median (boot mean D − point D) = -0.0091, max |.| = 0.0309  
Max Monte Carlo SE of P upper bound: 1.67

## H2 (registered: point rule; bootstrap share = uncertainty)

| domain   |   n_exceed_point_linear |   n_exceed_point_log |   mean_share_exceed_linear |   mean_share_exceed_log |   max_share_exceed_linear |
|:---------|------------------------:|---------------------:|---------------------------:|------------------------:|--------------------------:|
| A        |                       1 |                    0 |                      0.069 |                   0.032 |                     0.809 |
| K        |                       0 |                    0 |                      0     |                   0     |                     0     |
| S        |                       0 |                    0 |                      0     |                   0     |                     0     |


## H1: feeder -> family, 97.5th percentile of P (close if <= 25)

| domain   | feeder   | feeder_role      |   P_point |   P_hi | close_rule   | domain_interpretable   |   n_draws_P_above_thr |   p_one_sided |
|:---------|:---------|:-----------------|----------:|-------:|:-------------|:-----------------------|----------------------:|--------------:|
| A        | 51-9161  | feeder_core      |      1.88 |   3.31 | True         | False                  |                     0 |          0    |
| A        | 51-4041  | feeder_core      |      6.52 |   9.72 | True         | False                  |                     0 |          0    |
| A        | 51-4081  | feeder_core      |     10.17 |  13.7  | True         | False                  |                     0 |          0    |
| A        | 51-2031  | feeder_core      |     16.91 |  19.45 | True         | False                  |                     0 |          0    |
| A        | 51-9124  | feeder_core      |     17.46 |  22.54 | True         | False                  |                     1 |          0    |
| A        | 51-4072  | feeder_core      |     19.23 |  23.2  | True         | False                  |                     2 |          0    |
| A        | 51-4031  | feeder_core      |     20.33 |  24.09 | True         | False                  |                     6 |          0.01 |
| A        | 51-4122  | feeder_core      |     30.94 |  34.26 | False        | False                  |                   998 |          1    |
| A        | 51-9061  | feeder_core      |     31.05 |  34.92 | False        | False                  |                   999 |          1    |
| A        | 51-2090  | feeder_core      |     33.26 |  37.35 | False        | False                  |                   998 |          1    |
| A        | 51-4121  | feeder_core      |     35.69 |  44.31 | False        | False                  |                  1000 |          1    |
| A        | 53-7062  | negative_control |     40.66 |  44.42 | False        | False                  |                  1000 |          1    |
| A        | 51-2028  | feeder_core      |     43.31 |  45.86 | False        | False                  |                  1000 |          1    |
| K        | 51-2090  | feeder_core      |      9.39 |  18.45 | True         | True                   |                     0 |          0    |
| K        | 51-9161  | feeder_core      |     16.24 |  25.75 | False        | True                   |                    40 |          0.04 |
| K        | 51-9061  | feeder_core      |     22.54 |  37.46 | False        | True                   |                   490 |          0.49 |
| K        | 51-2031  | feeder_core      |     24.2  |  38.46 | False        | True                   |                   597 |          0.6  |
| K        | 51-4081  | feeder_core      |     28.18 |  48.07 | False        | True                   |                   886 |          0.89 |
| K        | 51-4122  | feeder_core      |     38.56 |  57.24 | False        | True                   |                   983 |          0.98 |
| K        | 51-4041  | feeder_core      |     48.4  |  74.81 | False        | True                   |                  1000 |          1    |
| K        | 51-4121  | feeder_core      |     55.58 |  72.71 | False        | True                   |                  1000 |          1    |
| K        | 51-4072  | feeder_core      |     58.01 |  74.15 | False        | True                   |                  1000 |          1    |
| K        | 53-7062  | negative_control |     67.62 |  86.86 | False        | True                   |                  1000 |          1    |
| K        | 51-2028  | feeder_core      |     76.91 |  85.19 | False        | True                   |                  1000 |          1    |
| K        | 51-4031  | feeder_core      |     96.57 |  99.12 | False        | True                   |                  1000 |          1    |
| K        | 51-9124  | feeder_core      |     98.12 |  99.34 | False        | True                   |                  1000 |          1    |
| S        | 51-9161  | feeder_core      |      5.97 |   8.62 | True         | True                   |                     0 |          0    |
| S        | 51-4081  | feeder_core      |      8.07 |  10.17 | True         | True                   |                     0 |          0    |
| S        | 51-4041  | feeder_core      |      9.06 |  12.71 | True         | True                   |                     0 |          0    |
| S        | 51-2031  | feeder_core      |     29.28 |  34.7  | False        | True                   |                   918 |          0.92 |
| S        | 51-9061  | feeder_core      |     33.7  |  42.43 | False        | True                   |                   998 |          1    |
| S        | 51-2090  | feeder_core      |     35.14 |  40.99 | False        | True                   |                  1000 |          1    |
| S        | 51-4031  | feeder_core      |     37.46 |  44.75 | False        | True                   |                  1000 |          1    |
| S        | 51-9124  | feeder_core      |     43.54 |  50.61 | False        | True                   |                  1000 |          1    |
| S        | 51-4072  | feeder_core      |     43.65 |  51.16 | False        | True                   |                  1000 |          1    |
| S        | 51-4122  | feeder_core      |     44.86 |  51.16 | False        | True                   |                  1000 |          1    |
| S        | 51-2028  | feeder_core      |     53.81 |  60.67 | False        | True                   |                  1000 |          1    |
| S        | 51-4121  | feeder_core      |     88.73 |  92.93 | False        | True                   |                  1000 |          1    |
| S        | 53-7062  | negative_control |     94.59 |  95.14 | False        | True                   |                  1000 |          1    |


## H1-group (DL-8, not blind)

| domain   |   diff_mean_P_mw_minus_asm |   exact_p_one_sided |   n_permutations |   boot_share_diff_lt_0 |   diff_lo |   diff_hi |   mean_P_machining_setup |   mean_P_welding |   mean_P_assembly | domain_interpretable   | label            |
|:---------|---------------------------:|--------------------:|-----------------:|-----------------------:|----------:|----------:|-------------------------:|-----------------:|------------------:|:-----------------------|:-----------------|
| A        |                   -13.3386 |              0.1    |              120 |                  1     |  -15.296  |   -9.6972 |                  11.6243 |          33.3149 |           31.1602 | False                  | not blind (DL-8) |
| K        |                    11.96   |              0.7167 |              120 |                  0     |    5.7298 |   21.327  |                  49.4807 |          47.0718 |           36.8324 | True                   | not blind (DL-8) |
| S        |                    -5.4407 |              0.375  |              120 |                  0.998 |  -10.0399 |   -1.3979 |                  20.8398 |          66.7956 |           39.4107 | True                   | not blind (DL-8) |


## N_eff — EXPLORATORY (DL-9)

| domain   | feeder   | feeder_role   |   neff_point |   neff_lo |   neff_hi |   n_elements_in_domain |   neff_pct_reference |   neff_pct_reference_lo |   neff_pct_reference_hi |   neff_pct_local |   neff_pct_local_lo |   neff_pct_local_hi | label              |
|:---------|:---------|:--------------|-------------:|----------:|----------:|-----------------------:|---------------------:|------------------------:|------------------------:|-----------------:|--------------------:|--------------------:|:-------------------|
| A        | 51-2090  | feeder_core   |        32.56 |     27.86 |     33.99 |                     52 |                90.83 |                   73.48 |                   95.14 |               98 |               86    |              100    | EXPLORATORY (DL-9) |
| A        | 51-4031  | feeder_core   |        26.64 |     23.22 |     28.78 |                     52 |                58.9  |                   30.94 |                   76.02 |               83 |               68    |               94    | EXPLORATORY (DL-9) |
| A        | 51-2031  | feeder_core   |        25.49 |     21.25 |     29.21 |                     52 |                47.62 |                   18.78 |                   78.24 |               84 |               47    |               99    | EXPLORATORY (DL-9) |
| A        | 51-9061  | feeder_core   |        29.61 |     26.73 |     31.7  |                     52 |                79.67 |                   64.64 |                   89.62 |               92 |               82    |               98    | EXPLORATORY (DL-9) |
| A        | 51-4121  | feeder_core   |        28.56 |     22.36 |     30.27 |                     52 |                73.7  |                   22.98 |                   85.3  |               82 |               25    |               93    | EXPLORATORY (DL-9) |
| A        | 51-4081  | feeder_core   |        26.7  |     21.27 |     29.43 |                     52 |                59.34 |                   18.78 |                   80.35 |               96 |               67.97 |              100    | EXPLORATORY (DL-9) |
| A        | 51-4041  | feeder_core   |        18.72 |     15.72 |     22.76 |                     52 |                 8.62 |                    5.74 |                   23.98 |               47 |               26    |               80    | EXPLORATORY (DL-9) |
| A        | 51-2028  | feeder_core   |        36.87 |     33.69 |     38.15 |                     52 |                98.23 |                   94.92 |                   99.56 |              100 |               98    |              100    | EXPLORATORY (DL-9) |
| A        | 51-9161  | feeder_core   |        13.67 |      9.44 |     16.94 |                     52 |                 3.65 |                    0.88 |                    6.52 |               33 |                7    |               51.02 | EXPLORATORY (DL-9) |
| A        | 51-4072  | feeder_core   |        27.69 |     22.13 |     30.02 |                     52 |                67.73 |                   22.54 |                   83.65 |               95 |               53    |               99    | EXPLORATORY (DL-9) |
| A        | 51-4122  | feeder_core   |        30.57 |     26.63 |     32.29 |                     52 |                84.2  |                   63.31 |                   90.94 |               95 |               81    |               99    | EXPLORATORY (DL-9) |
| A        | 51-9124  | feeder_core   |        27.08 |     21.92 |     28.59 |                     52 |                62.1  |                   20.88 |                   76.02 |               90 |               49.98 |               97    | EXPLORATORY (DL-9) |
| K        | 51-2090  | feeder_core   |         3.68 |      2.63 |      8.07 |                     33 |                18.05 |                    7.3  |                   79.25 |               62 |               30    |               97    | EXPLORATORY (DL-9) |
| K        | 51-4031  | feeder_core   |        17.11 |     11    |     17.28 |                     33 |                99.78 |                   95.02 |                  100    |               99 |               86    |              100    | EXPLORATORY (DL-9) |
| K        | 51-2031  | feeder_core   |         8.44 |      5.49 |     12.17 |                     33 |                84.83 |                   45.08 |                   97.13 |               92 |               65.97 |              100    | EXPLORATORY (DL-9) |
| K        | 51-9061  | feeder_core   |         5.54 |      3.71 |      9.01 |                     33 |                47.84 |                   18.02 |                   85.86 |               68 |               35    |               94    | EXPLORATORY (DL-9) |
| K        | 51-4121  | feeder_core   |        13.19 |      8.82 |     15.79 |                     33 |                98.23 |                   88.06 |                   99.89 |               99 |               88    |              100    | EXPLORATORY (DL-9) |
| K        | 51-4081  | feeder_core   |         6.61 |      5.09 |     11.21 |                     33 |                64.78 |                   37.01 |                   95.03 |               74 |               53    |               99    | EXPLORATORY (DL-9) |
| K        | 51-4041  | feeder_core   |        10.13 |      7.3  |     13.63 |                     33 |                91.92 |                   72.53 |                   98.9  |               94 |               75    |              100    | EXPLORATORY (DL-9) |
| K        | 51-2028  | feeder_core   |        14.41 |     10.97 |     15.99 |                     33 |                98.89 |                   95.91 |                   99.89 |              100 |               95    |              100    | EXPLORATORY (DL-9) |
| K        | 51-9161  | feeder_core   |         3.44 |      2.6  |      7.55 |                     33 |                16.06 |                    7.51 |                   75.49 |               39 |               21    |               91    | EXPLORATORY (DL-9) |
| K        | 51-4072  | feeder_core   |        11.54 |      8.06 |     14.04 |                     33 |                95.24 |                   83.29 |                   98.9  |               94 |               83.98 |              100    | EXPLORATORY (DL-9) |
| K        | 51-4122  | feeder_core   |        10.24 |      6.39 |     13.63 |                     33 |                92.14 |                   62.49 |                   98.79 |               95 |               69    |              100    | EXPLORATORY (DL-9) |
| K        | 51-9124  | feeder_core   |        15.94 |     12.05 |     16.96 |                     33 |                99.45 |                   97.68 |                  100    |               98 |               92    |              100    | EXPLORATORY (DL-9) |
| S        | 51-2090  | feeder_core   |        13.62 |     12.23 |     15    |                     35 |                73.26 |                   71.16 |                   77.68 |               79 |               71    |               82    | EXPLORATORY (DL-9) |
| S        | 51-4031  | feeder_core   |        19.59 |     16.78 |     21.24 |                     35 |                87.85 |                   82.76 |                   93.48 |               93 |               85    |               97    | EXPLORATORY (DL-9) |
| S        | 51-2031  | feeder_core   |        21.04 |     18.01 |     22.65 |                     35 |                91.93 |                   85.75 |                   96.24 |               97 |               91    |              100    | EXPLORATORY (DL-9) |
| S        | 51-9061  | feeder_core   |        11.34 |      9.83 |     12.95 |                     35 |                66.85 |                   60.1  |                   72.04 |               72 |               65    |               77    | EXPLORATORY (DL-9) |
| S        | 51-4121  | feeder_core   |        23.14 |     19.35 |     24.21 |                     35 |                96.13 |                   89.06 |                   97.9  |               94 |               81    |               99    | EXPLORATORY (DL-9) |
| S        | 51-4081  | feeder_core   |        13.83 |     10.96 |     16.59 |                     35 |                73.92 |                   65.52 |                   80.88 |               87 |               76    |               96    | EXPLORATORY (DL-9) |
| S        | 51-4041  | feeder_core   |        15.21 |     11.93 |     17.42 |                     35 |                78.23 |                   69.94 |                   83.54 |               93 |               79    |               97    | EXPLORATORY (DL-9) |
| S        | 51-2028  | feeder_core   |        22.84 |     20.06 |     23.79 |                     35 |                95.58 |                   91.16 |                   97.35 |               96 |               92    |              100    | EXPLORATORY (DL-9) |
| S        | 51-9161  | feeder_core   |         9.85 |      7.83 |     12.34 |                     35 |                60.22 |                   29.61 |                   69.72 |               71 |               54    |               80    | EXPLORATORY (DL-9) |
| S        | 51-4072  | feeder_core   |        20.2  |     17.69 |     21.19 |                     35 |                89.94 |                   84.75 |                   93.48 |               90 |               84    |               97    | EXPLORATORY (DL-9) |
| S        | 51-4122  | feeder_core   |        17.95 |     15.87 |     19.48 |                     35 |                83.87 |                   80.44 |                   88.29 |               80 |               78    |               91    | EXPLORATORY (DL-9) |
| S        | 51-9124  | feeder_core   |        20.03 |     17.36 |     21.46 |                     35 |                89.06 |                   84.09 |                   93.69 |               87 |               84    |               97    | EXPLORATORY (DL-9) |
