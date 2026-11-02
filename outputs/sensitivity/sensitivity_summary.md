# Sensitivity analyses (DL-15 – DL-20)

## Uncertainty models — core feeders → family

| variant                             | domain   |   n_close |   median_P_width |   max_exceed_share |
|:------------------------------------|:---------|----------:|-----------------:|-------------------:|
| comonotone                          | A        |         1 |           32     |              0.719 |
| comonotone                          | K        |         0 |           74.091 |              0.001 |
| comonotone                          | S        |         2 |           60.68  |              0.01  |
| copula                              | A        |         4 |           16.302 |              0.724 |
| copula                              | K        |         0 |           49.894 |              0     |
| copula                              | S        |         3 |           35.591 |              0.002 |
| mi_se                               | A        |         7 |            7.569 |              0.793 |
| mi_se                               | K        |         1 |           22.988 |              0     |
| mi_se                               | S        |         3 |           14.366 |              0     |
| registered (independent, median SE) | A        |         7 |            7.572 |              0.809 |
| registered (independent, median SE) | K        |         1 |           23.322 |              0     |
| registered (independent, median SE) | S        |         3 |           14.366 |              0     |


H1 decision changes vs registered: comonotone: A 51-4031 → not close; comonotone: A 51-2031 → not close; comonotone: A 51-4081 → not close; comonotone: A 51-4041 → not close; comonotone: A 51-4072 → not close; comonotone: A 51-9124 → not close; comonotone: K 51-2090 → not close; comonotone: S 51-4041 → not close; copula: A 51-4031 → not close; copula: A 51-4072 → not close; copula: A 51-9124 → not close; copula: K 51-2090 → not close


## distances

| domain   | metric                                     | feeder                 | role             |   value |   percentile |
|:---------|:-------------------------------------------|:-----------------------|:-----------------|--------:|-------------:|
| A        | D (registered)                             | 51-2090                | feeder_core      |   0.648 |       33.26  |
| A        | D (registered)                             | 51-4031                | feeder_core      |   0.496 |       20.331 |
| A        | D (registered)                             | 51-2031                | feeder_core      |   0.45  |       16.906 |
| A        | D (registered)                             | 51-9061                | feeder_core      |   0.622 |       31.05  |
| A        | D (registered)                             | 51-4121                | feeder_core      |   0.679 |       35.691 |
| A        | D (registered)                             | 51-4081                | feeder_core      |   0.37  |       10.166 |
| A        | D (registered)                             | 51-4041                | feeder_core      |   0.302 |        6.519 |
| A        | D (registered)                             | 51-2028                | feeder_core      |   0.765 |       43.315 |
| A        | D (registered)                             | 51-9161                | feeder_core      |   0.168 |        1.878 |
| A        | D (registered)                             | 51-4072                | feeder_core      |   0.476 |       19.227 |
| A        | D (registered)                             | 51-4122                | feeder_core      |   0.621 |       30.939 |
| A        | D (registered)                             | 51-9124                | feeder_core      |   0.462 |       17.459 |
| A        | D (registered)                             | 51-1011                | sensitivity      |   0.485 |       20.11  |
| A        | D (registered)                             | 51-4111                | sensitivity      |   0.436 |       15.359 |
| A        | D (registered)                             | 17-3026                | sensitivity      |   0.818 |       47.293 |
| A        | D (registered)                             | 53-7062                | negative_control |   0.733 |       40.663 |
| A        | weighted Euclidean (non-directional)       | 51-2090                | feeder_core      |   0.822 |       19.227 |
| A        | weighted Euclidean (non-directional)       | 51-4031                | feeder_core      |   0.678 |       10.055 |
| A        | weighted Euclidean (non-directional)       | 51-2031                | feeder_core      |   0.618 |        6.519 |
| A        | weighted Euclidean (non-directional)       | 51-9061                | feeder_core      |   0.838 |       20.11  |
| A        | weighted Euclidean (non-directional)       | 51-4121                | feeder_core      |   0.884 |       23.094 |
| A        | weighted Euclidean (non-directional)       | 51-4081                | feeder_core      |   0.591 |        4.862 |
| A        | weighted Euclidean (non-directional)       | 51-4041                | feeder_core      |   0.523 |        3.094 |
| A        | weighted Euclidean (non-directional)       | 51-2028                | feeder_core      |   0.979 |       28.84  |
| A        | weighted Euclidean (non-directional)       | 51-9161                | feeder_core      |   0.502 |        1.878 |
| A        | weighted Euclidean (non-directional)       | 51-4072                | feeder_core      |   0.636 |        7.514 |
| A        | weighted Euclidean (non-directional)       | 51-4122                | feeder_core      |   0.805 |       17.79  |
| A        | weighted Euclidean (non-directional)       | 51-9124                | feeder_core      |   0.626 |        6.961 |
| A        | weighted Euclidean (non-directional)       | 51-1011                | sensitivity      |   0.823 |       19.337 |
| A        | weighted Euclidean (non-directional)       | 51-4111                | sensitivity      |   0.765 |       15.912 |
| A        | weighted Euclidean (non-directional)       | 17-3026                | sensitivity      |   1.321 |       48.177 |
| A        | weighted Euclidean (non-directional)       | 53-7062                | negative_control |   0.975 |       28.508 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-2090                | feeder_core      |   7.489 |       15.249 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4031                | feeder_core      |   7.922 |       29.834 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-2031                | feeder_core      |   7.671 |       20.663 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-9061                | feeder_core      |   7.611 |       18.232 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4121                | feeder_core      |  10.228 |       92.155 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4081                | feeder_core      |   8.069 |       36.133 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4041                | feeder_core      |   7.751 |       22.983 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-2028                | feeder_core      |   7.076 |        7.182 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-9161                | feeder_core      |   7.108 |        7.624 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4072                | feeder_core      |   8.661 |       57.459 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4122                | feeder_core      |   9.112 |       71.602 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-9124                | feeder_core      |   8.337 |       46.851 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-1011                | sensitivity      |   7.412 |       13.923 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4111                | sensitivity      |   8.791 |       61.989 |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 17-3026                | sensitivity      |   7.186 |        8.95  |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | 53-7062                | negative_control |   9.329 |       77.127 |
| A        | D (registered)                             | __spearman_vs_D_core__ | summary          |   1     |      nan     |
| A        | weighted Euclidean (non-directional)       | __spearman_vs_D_core__ | summary          |   0.993 |      nan     |
| A        | Mahalanobis, Ledoit-Wolf (non-directional) | __spearman_vs_D_core__ | summary          |   0.021 |      nan     |
| K        | D (registered)                             | 51-2090                | feeder_core      |   0.102 |        9.392 |
| K        | D (registered)                             | 51-4031                | feeder_core      |   0.992 |       96.575 |
| K        | D (registered)                             | 51-2031                | feeder_core      |   0.229 |       24.199 |
| K        | D (registered)                             | 51-9061                | feeder_core      |   0.216 |       22.541 |
| K        | D (registered)                             | 51-4121                | feeder_core      |   0.533 |       55.58  |
| K        | D (registered)                             | 51-4081                | feeder_core      |   0.27  |       28.177 |
| K        | D (registered)                             | 51-4041                | feeder_core      |   0.473 |       48.398 |
| K        | D (registered)                             | 51-2028                | feeder_core      |   0.712 |       76.906 |
| K        | D (registered)                             | 51-9161                | feeder_core      |   0.167 |       16.243 |
| K        | D (registered)                             | 51-4072                | feeder_core      |   0.548 |       58.011 |
| K        | D (registered)                             | 51-4122                | feeder_core      |   0.375 |       38.564 |
| K        | D (registered)                             | 51-9124                | feeder_core      |   1.062 |       98.122 |
| K        | D (registered)                             | 51-1011                | sensitivity      |   0.16  |       15.249 |
| K        | D (registered)                             | 51-4111                | sensitivity      |   0.329 |       34.475 |
| K        | D (registered)                             | 17-3026                | sensitivity      |   0.049 |        3.536 |
| K        | D (registered)                             | 53-7062                | negative_control |   0.629 |       67.624 |
| K        | weighted Euclidean (non-directional)       | 51-2090                | feeder_core      |   0.55  |        1.878 |
| K        | weighted Euclidean (non-directional)       | 51-4031                | feeder_core      |   1.085 |       30.829 |
| K        | weighted Euclidean (non-directional)       | 51-2031                | feeder_core      |   0.529 |        0.994 |
| K        | weighted Euclidean (non-directional)       | 51-9061                | feeder_core      |   0.583 |        2.983 |
| K        | weighted Euclidean (non-directional)       | 51-4121                | feeder_core      |   0.65  |        6.519 |
| K        | weighted Euclidean (non-directional)       | 51-4081                | feeder_core      |   0.545 |        1.657 |
| K        | weighted Euclidean (non-directional)       | 51-4041                | feeder_core      |   0.682 |        8.619 |
| K        | weighted Euclidean (non-directional)       | 51-2028                | feeder_core      |   0.833 |       16.575 |
| K        | weighted Euclidean (non-directional)       | 51-9161                | feeder_core      |   0.626 |        5.083 |
| K        | weighted Euclidean (non-directional)       | 51-4072                | feeder_core      |   0.747 |       12.597 |
| K        | weighted Euclidean (non-directional)       | 51-4122                | feeder_core      |   0.79  |       14.144 |
| K        | weighted Euclidean (non-directional)       | 51-9124                | feeder_core      |   1.169 |       37.127 |
| K        | weighted Euclidean (non-directional)       | 51-1011                | sensitivity      |   0.896 |       20.221 |
| K        | weighted Euclidean (non-directional)       | 51-4111                | sensitivity      |   0.625 |        4.862 |
| K        | weighted Euclidean (non-directional)       | 17-3026                | sensitivity      |   1.024 |       26.851 |
| K        | weighted Euclidean (non-directional)       | 53-7062                | negative_control |   1.039 |       28.066 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-2090                | feeder_core      |   3.533 |        0.552 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4031                | feeder_core      |   4.881 |       11.16  |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-2031                | feeder_core      |   4.45  |        5.967 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-9061                | feeder_core      |   4.566 |        7.182 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4121                | feeder_core      |   3.75  |        1.215 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4081                | feeder_core      |   4.478 |        6.077 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4041                | feeder_core      |   4.829 |       10.387 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-2028                | feeder_core      |   3.9   |        1.878 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-9161                | feeder_core      |   4.125 |        3.867 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4072                | feeder_core      |   4.286 |        5.083 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4122                | feeder_core      |   6.545 |       62.32  |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-9124                | feeder_core      |   4.687 |        8.619 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-1011                | sensitivity      |   5.188 |       18.564 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4111                | sensitivity      |   5.327 |       21.326 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 17-3026                | sensitivity      |   5.007 |       14.144 |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | 53-7062                | negative_control |   6.034 |       43.978 |
| K        | D (registered)                             | __spearman_vs_D_core__ | summary          |   1     |      nan     |
| K        | weighted Euclidean (non-directional)       | __spearman_vs_D_core__ | summary          |   0.839 |      nan     |
| K        | Mahalanobis, Ledoit-Wolf (non-directional) | __spearman_vs_D_core__ | summary          |   0.329 |      nan     |
| S        | D (registered)                             | 51-2090                | feeder_core      |   0.722 |       35.138 |
| S        | D (registered)                             | 51-4031                | feeder_core      |   0.747 |       37.459 |
| S        | D (registered)                             | 51-2031                | feeder_core      |   0.666 |       29.282 |
| S        | D (registered)                             | 51-9061                | feeder_core      |   0.708 |       33.702 |
| S        | D (registered)                             | 51-4121                | feeder_core      |   1.201 |       88.729 |
| S        | D (registered)                             | 51-4081                | feeder_core      |   0.328 |        8.066 |
| S        | D (registered)                             | 51-4041                | feeder_core      |   0.351 |        9.061 |
| S        | D (registered)                             | 51-2028                | feeder_core      |   0.885 |       53.812 |
| S        | D (registered)                             | 51-9161                | feeder_core      |   0.285 |        5.967 |
| S        | D (registered)                             | 51-4072                | feeder_core      |   0.795 |       43.646 |
| S        | D (registered)                             | 51-4122                | feeder_core      |   0.803 |       44.862 |
| S        | D (registered)                             | 51-9124                | feeder_core      |   0.794 |       43.536 |
| S        | D (registered)                             | 51-1011                | sensitivity      |   0.399 |       11.602 |
| S        | D (registered)                             | 51-4111                | sensitivity      |   0.505 |       17.569 |
| S        | D (registered)                             | 17-3026                | sensitivity      |   0.446 |       13.812 |
| S        | D (registered)                             | 53-7062                | negative_control |   1.37  |       94.586 |
| S        | weighted Euclidean (non-directional)       | 51-2090                | feeder_core      |   1.083 |       21.215 |
| S        | weighted Euclidean (non-directional)       | 51-4031                | feeder_core      |   0.977 |       16.243 |
| S        | weighted Euclidean (non-directional)       | 51-2031                | feeder_core      |   0.814 |        9.613 |
| S        | weighted Euclidean (non-directional)       | 51-9061                | feeder_core      |   1.112 |       22.32  |
| S        | weighted Euclidean (non-directional)       | 51-4121                | feeder_core      |   1.339 |       32.818 |
| S        | weighted Euclidean (non-directional)       | 51-4081                | feeder_core      |   0.495 |        2.983 |
| S        | weighted Euclidean (non-directional)       | 51-4041                | feeder_core      |   0.476 |        2.32  |
| S        | weighted Euclidean (non-directional)       | 51-2028                | feeder_core      |   1.008 |       17.79  |
| S        | weighted Euclidean (non-directional)       | 51-9161                | feeder_core      |   0.559 |        4.862 |
| S        | weighted Euclidean (non-directional)       | 51-4072                | feeder_core      |   1.001 |       17.348 |
| S        | weighted Euclidean (non-directional)       | 51-4122                | feeder_core      |   1.05  |       20.11  |
| S        | weighted Euclidean (non-directional)       | 51-9124                | feeder_core      |   1.014 |       18.564 |
| S        | weighted Euclidean (non-directional)       | 51-1011                | sensitivity      |   1.282 |       29.613 |
| S        | weighted Euclidean (non-directional)       | 51-4111                | sensitivity      |   0.824 |        9.945 |
| S        | weighted Euclidean (non-directional)       | 17-3026                | sensitivity      |   1.315 |       31.602 |
| S        | weighted Euclidean (non-directional)       | 53-7062                | negative_control |   1.523 |       43.536 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-2090                | feeder_core      |   7.209 |       47.956 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4031                | feeder_core      |   6.475 |       18.785 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-2031                | feeder_core      |   5.815 |        7.735 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-9061                | feeder_core      |   5.989 |        9.171 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4121                | feeder_core      |   8.245 |       85.304 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4081                | feeder_core      |   4.766 |        1.547 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4041                | feeder_core      |   4.206 |        0.994 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-2028                | feeder_core      |   4.558 |        1.105 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-9161                | feeder_core      |   6.008 |        9.613 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4072                | feeder_core      |   7.847 |       75.138 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4122                | feeder_core      |   7.349 |       54.586 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-9124                | feeder_core      |   7.102 |       42.983 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-1011                | sensitivity      |   6.91  |       35.691 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 51-4111                | sensitivity      |   7.194 |       47.403 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 17-3026                | sensitivity      |   8.644 |       91.713 |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | 53-7062                | negative_control |   6.902 |       35.028 |
| S        | D (registered)                             | __spearman_vs_D_core__ | summary          |   1     |      nan     |
| S        | weighted Euclidean (non-directional)       | __spearman_vs_D_core__ | summary          |   0.685 |      nan     |
| S        | Mahalanobis, Ledoit-Wolf (non-directional) | __spearman_vs_D_core__ | summary          |   0.566 |      nan     |

## abilities_subgroups

| group       |   n_elements | feeder   | role             |     D |      P |
|:------------|-------------:|:---------|:-----------------|------:|-------:|
| all         |           52 | 51-2090  | feeder_core      | 0.648 | 33.26  |
| all         |           52 | 51-4031  | feeder_core      | 0.496 | 20.331 |
| all         |           52 | 51-2031  | feeder_core      | 0.45  | 16.906 |
| all         |           52 | 51-9061  | feeder_core      | 0.622 | 31.05  |
| all         |           52 | 51-4121  | feeder_core      | 0.679 | 35.691 |
| all         |           52 | 51-4081  | feeder_core      | 0.37  | 10.166 |
| all         |           52 | 51-4041  | feeder_core      | 0.302 |  6.519 |
| all         |           52 | 51-2028  | feeder_core      | 0.765 | 43.315 |
| all         |           52 | 51-9161  | feeder_core      | 0.168 |  1.878 |
| all         |           52 | 51-4072  | feeder_core      | 0.476 | 19.227 |
| all         |           52 | 51-4122  | feeder_core      | 0.621 | 30.939 |
| all         |           52 | 51-9124  | feeder_core      | 0.462 | 17.459 |
| all         |           52 | 51-1011  | sensitivity      | 0.485 | 20.11  |
| all         |           52 | 51-4111  | sensitivity      | 0.436 | 15.359 |
| all         |           52 | 17-3026  | sensitivity      | 0.818 | 47.293 |
| all         |           52 | 53-7062  | negative_control | 0.733 | 40.663 |
| cognitive   |           21 | 51-2090  | feeder_core      | 0.63  | 76.464 |
| cognitive   |           21 | 51-4031  | feeder_core      | 0.588 | 72.928 |
| cognitive   |           21 | 51-2031  | feeder_core      | 0.448 | 61.326 |
| cognitive   |           21 | 51-9061  | feeder_core      | 0.45  | 61.657 |
| cognitive   |           21 | 51-4121  | feeder_core      | 0.777 | 85.083 |
| cognitive   |           21 | 51-4081  | feeder_core      | 0.32  | 47.403 |
| cognitive   |           21 | 51-4041  | feeder_core      | 0.233 | 36.354 |
| cognitive   |           21 | 51-2028  | feeder_core      | 0.58  | 72.265 |
| cognitive   |           21 | 51-9161  | feeder_core      | 0.104 | 12.597 |
| cognitive   |           21 | 51-4072  | feeder_core      | 0.57  | 71.16  |
| cognitive   |           21 | 51-4122  | feeder_core      | 0.697 | 80.663 |
| cognitive   |           21 | 51-9124  | feeder_core      | 0.616 | 75.028 |
| cognitive   |           21 | 51-1011  | sensitivity      | 0.161 | 23.315 |
| cognitive   |           21 | 51-4111  | sensitivity      | 0.3   | 45.083 |
| cognitive   |           21 | 17-3026  | sensitivity      | 0.076 |  7.403 |
| cognitive   |           21 | 53-7062  | negative_control | 0.94  | 91.381 |
| psychomotor |           10 | 51-2090  | feeder_core      | 0.477 | 24.309 |
| psychomotor |           10 | 51-4031  | feeder_core      | 0.23  |  9.061 |
| psychomotor |           10 | 51-2031  | feeder_core      | 0.292 | 12.486 |
| psychomotor |           10 | 51-9061  | feeder_core      | 0.696 | 34.365 |
| psychomotor |           10 | 51-4121  | feeder_core      | 0.477 | 24.42  |
| psychomotor |           10 | 51-4081  | feeder_core      | 0.278 | 11.713 |
| psychomotor |           10 | 51-4041  | feeder_core      | 0.102 |  2.431 |
| psychomotor |           10 | 51-2028  | feeder_core      | 0.656 | 33.37  |
| psychomotor |           10 | 51-9161  | feeder_core      | 0.066 |  1.215 |
| psychomotor |           10 | 51-4072  | feeder_core      | 0.338 | 15.359 |
| psychomotor |           10 | 51-4122  | feeder_core      | 0.427 | 21.105 |
| psychomotor |           10 | 51-9124  | feeder_core      | 0.282 | 11.823 |
| psychomotor |           10 | 51-1011  | sensitivity      | 0.524 | 26.961 |
| psychomotor |           10 | 51-4111  | sensitivity      | 0.184 |  5.746 |
| psychomotor |           10 | 17-3026  | sensitivity      | 1.362 | 55.47  |
| psychomotor |           10 | 53-7062  | negative_control | 0.429 | 21.326 |
| physical    |            9 | 51-2090  | feeder_core      | 0.562 | 27.735 |
| physical    |            9 | 51-4031  | feeder_core      | 0.421 | 20.221 |
| physical    |            9 | 51-2031  | feeder_core      | 0.59  | 28.84  |
| physical    |            9 | 51-9061  | feeder_core      | 0.979 | 42.099 |
| physical    |            9 | 51-4121  | feeder_core      | 0.503 | 24.42  |
| physical    |            9 | 51-4081  | feeder_core      | 0.528 | 25.083 |
| physical    |            9 | 51-4041  | feeder_core      | 0.382 | 18.232 |
| physical    |            9 | 51-2028  | feeder_core      | 1.089 | 45.746 |
| physical    |            9 | 51-9161  | feeder_core      | 0.534 | 26.077 |
| physical    |            9 | 51-4072  | feeder_core      | 0.185 |  9.061 |
| physical    |            9 | 51-4122  | feeder_core      | 0.466 | 22.541 |
| physical    |            9 | 51-9124  | feeder_core      | 0.243 | 12.155 |
| physical    |            9 | 51-1011  | sensitivity      | 0.883 | 38.122 |
| physical    |            9 | 51-4111  | sensitivity      | 0.652 | 31.271 |
| physical    |            9 | 17-3026  | sensitivity      | 1.833 | 62.099 |
| physical    |            9 | 53-7062  | negative_control | 0.173 |  8.508 |
| sensory     |           12 | 51-2090  | feeder_core      | 0.915 | 40.442 |
| sensory     |           12 | 51-4031  | feeder_core      | 0.641 | 22.32  |
| sensory     |           12 | 51-2031  | feeder_core      | 0.521 | 15.249 |
| sensory     |           12 | 51-9061  | feeder_core      | 0.634 | 21.768 |
| sensory     |           12 | 51-4121  | feeder_core      | 0.814 | 33.591 |
| sensory     |           12 | 51-4081  | feeder_core      | 0.452 | 11.713 |
| sensory     |           12 | 51-4041  | feeder_core      | 0.583 | 19.227 |
| sensory     |           12 | 51-2028  | feeder_core      | 1.013 | 48.177 |
| sensory     |           12 | 51-9161  | feeder_core      | 0.147 |  2.32  |
| sensory     |           12 | 51-4072  | feeder_core      | 0.634 | 21.547 |
| sensory     |           12 | 51-4122  | feeder_core      | 0.778 | 30.497 |
| sensory     |           12 | 51-9124  | feeder_core      | 0.494 | 13.812 |
| sensory     |           12 | 51-1011  | sensitivity      | 0.797 | 32.044 |
| sensory     |           12 | 51-4111  | sensitivity      | 0.805 | 33.039 |
| sensory     |           12 | 17-3026  | sensitivity      | 1.005 | 47.624 |
| sensory     |           12 | 53-7062  | negative_control | 1.021 | 48.84  |

## vintage

| domain   | feeder   | role             |   n_universe |   P_vintage |   rpct_linear_vintage | exceed_linear_vintage   |      P |   h2_resid_pct_linear |
|:---------|:---------|:-----------------|-------------:|------------:|----------------------:|:------------------------|-------:|----------------------:|
| A        | 51-2090  | feeder_core      |          739 |      30.518 |                 1.09  | False                   | 33.26  |                 1.878 |
| A        | 51-4031  | feeder_core      |          739 |      18.665 |                19.619 | False                   | 20.331 |                23.867 |
| A        | 51-9061  | feeder_core      |          739 |      28.747 |                 2.044 | False                   | 31.05  |                 2.983 |
| A        | 51-4121  | feeder_core      |          739 |      32.97  |                12.398 | False                   | 35.691 |                14.365 |
| A        | 51-4081  | feeder_core      |          739 |       9.809 |                 2.316 | False                   | 10.166 |                 2.431 |
| A        | 51-4041  | feeder_core      |          739 |       5.858 |                58.447 | False                   |  6.519 |                61.878 |
| A        | 51-2028  | feeder_core      |          739 |      40.327 |                 1.499 | False                   | 43.315 |                 0.221 |
| A        | 51-9161  | feeder_core      |          739 |       1.907 |                97.956 | True                    |  1.878 |                97.459 |
| A        | 51-4122  | feeder_core      |          739 |      28.61  |                 3.134 | False                   | 30.939 |                 4.199 |
| A        | 51-9124  | feeder_core      |          739 |      15.395 |                 3.815 | False                   | 17.459 |                 5.414 |
| A        | 51-1011  | sensitivity      |          739 |      17.847 |                23.161 | False                   | 20.11  |                29.171 |
| A        | 51-4111  | sensitivity      |          739 |      13.896 |                67.302 | False                   | 15.359 |                66.298 |
| A        | 17-3026  | sensitivity      |          739 |      44.142 |                 6.948 | False                   | 47.293 |                 8.177 |
| A        | 53-7062  | negative_control |          739 |      37.33  |                17.166 | False                   | 40.663 |                20     |
| K        | 51-2090  | feeder_core      |          739 |       9.128 |                36.885 | False                   |  9.392 |                41.085 |
| K        | 51-4031  | feeder_core      |          739 |      97.003 |                 2.732 | False                   | 96.575 |                 3.544 |
| K        | 51-9061  | feeder_core      |          739 |      22.888 |                 9.29  | False                   | 22.541 |                11.739 |
| K        | 51-4121  | feeder_core      |          739 |      54.36  |                 0.956 | False                   | 55.58  |                 1.44  |
| K        | 51-4081  | feeder_core      |          739 |      28.338 |                 4.508 | False                   | 28.177 |                 6.534 |
| K        | 51-4041  | feeder_core      |          739 |      47.548 |                 4.645 | False                   | 48.398 |                 6.202 |
| K        | 51-2028  | feeder_core      |          739 |      96.594 |                 6.284 | False                   | 76.906 |                 1.883 |
| K        | 51-9161  | feeder_core      |          739 |      16.349 |                38.115 | False                   | 16.243 |                42.857 |
| K        | 51-4122  | feeder_core      |          739 |      37.33  |                 2.049 | False                   | 38.564 |                 2.658 |
| K        | 51-9124  | feeder_core      |          739 |      98.365 |                 6.011 | False                   | 98.122 |                 7.973 |
| K        | 51-1011  | sensitivity      |          739 |      15.123 |                70.902 | False                   | 15.249 |                73.976 |
| K        | 51-4111  | sensitivity      |          739 |      33.787 |                 1.366 | False                   | 34.475 |                 1.993 |
| K        | 17-3026  | sensitivity      |          739 |       3.542 |                60.109 | False                   |  3.536 |                64.12  |
| K        | 53-7062  | negative_control |          739 |      66.621 |                28.279 | False                   | 67.624 |                33.112 |
| S        | 51-2090  | feeder_core      |          739 |      33.651 |                16.757 | False                   | 35.138 |                20.442 |
| S        | 51-4031  | feeder_core      |          739 |      36.104 |                 4.632 | False                   | 37.459 |                 5.635 |
| S        | 51-9061  | feeder_core      |          739 |      32.561 |                24.659 | False                   | 33.702 |                29.613 |
| S        | 51-4121  | feeder_core      |          739 |      89.646 |                11.853 | False                   | 88.729 |                14.807 |
| S        | 51-4081  | feeder_core      |          739 |       7.493 |                 7.629 | False                   |  8.066 |                 9.392 |
| S        | 51-4041  | feeder_core      |          739 |       8.311 |                 6.403 | False                   |  9.061 |                 7.514 |
| S        | 51-2028  | feeder_core      |          739 |      49.591 |                15.668 | False                   | 53.812 |                 8.066 |
| S        | 51-9161  | feeder_core      |          739 |       5.45  |                18.392 | False                   |  5.967 |                22.32  |
| S        | 51-4122  | feeder_core      |          739 |      43.733 |                10.082 | False                   | 44.862 |                12.376 |
| S        | 51-9124  | feeder_core      |          739 |      42.779 |                 4.768 | False                   | 43.536 |                 5.525 |
| S        | 51-1011  | sensitivity      |          739 |      10.899 |                59.809 | False                   | 11.602 |                62.541 |
| S        | 51-4111  | sensitivity      |          739 |      17.03  |                 9.673 | False                   | 17.569 |                12.265 |
| S        | 17-3026  | sensitivity      |          739 |      12.943 |                93.597 | False                   | 13.812 |                94.696 |
| S        | 53-7062  | negative_control |          739 |      94.959 |                14.169 | False                   | 94.586 |                17.79  |

## Breadth alternatives (DL-18, inside the DL-19 bootstrap)

| domain   | feeder   |   neff_lo |   neff_hi |   expH_lo |   expH_hi |   k80_lo |   k80_hi |
|:---------|:---------|----------:|----------:|----------:|----------:|---------:|---------:|
| A        | 51-2090  |      28.2 |      33.8 |      33.9 |      38.5 |       24 |       27 |
| A        | 51-4031  |      23   |      28.9 |      29.6 |      35.2 |       21 |       25 |
| A        | 51-2031  |      21.2 |      29.2 |      29.5 |      35.5 |       21 |       26 |
| A        | 51-9061  |      26.5 |      32   |      31.3 |      36.3 |       22 |       26 |
| A        | 51-4121  |      22.1 |      30.9 |      29.2 |      36.3 |       21 |       26 |
| A        | 51-4081  |      21.4 |      29.5 |      27.7 |      33.9 |       20 |       25 |
| A        | 51-4041  |      15.9 |      22.6 |      21.1 |      28.1 |       15 |       20 |
| A        | 51-2028  |      33.5 |      38.1 |      38.1 |      42.4 |       26 |       30 |
| A        | 51-9161  |       9.7 |      17   |      13   |      20.3 |        9 |       15 |
| A        | 51-4072  |      22.1 |      30   |      28   |      34.7 |       20 |       24 |
| A        | 51-4122  |      26.8 |      32.4 |      32.6 |      37.9 |       22 |       26 |
| A        | 51-9124  |      21.8 |      28.5 |      27.4 |      33.5 |       19 |       24 |
| K        | 51-2090  |       2.5 |       7.9 |       3.6 |       9.6 |        3 |        7 |
| K        | 51-4031  |      10.9 |      17   |      15.1 |      20.8 |       10 |       14 |
| K        | 51-2031  |       5.3 |      12.2 |       7.9 |      15   |        5 |       10 |
| K        | 51-9061  |       3.6 |       9.1 |       5.2 |      11.4 |        4 |        8 |
| K        | 51-4121  |       9.1 |      15.6 |      12.9 |      19.4 |        8 |       13 |
| K        | 51-4081  |       5   |      11.3 |       7.5 |      14.4 |        5 |       10 |
| K        | 51-4041  |       7.1 |      14.2 |      10.2 |      17.6 |        7 |       12 |
| K        | 51-2028  |      10.9 |      16.3 |      14.6 |      19.9 |       10 |       14 |
| K        | 51-9161  |       2.6 |       7.3 |       4   |       9.8 |        3 |        7 |
| K        | 51-4072  |       8.2 |      14   |      12   |      18.3 |        8 |       13 |
| K        | 51-4122  |       6.4 |      13.6 |       9.5 |      16.6 |        7 |       11 |
| K        | 51-9124  |      12.2 |      16.7 |      16.3 |      20.6 |       10 |       14 |
| S        | 51-2090  |      12.3 |      15   |      16.1 |      19.2 |       12 |       14 |
| S        | 51-4031  |      16.8 |      21.3 |      22.5 |      26.5 |       16 |       20 |
| S        | 51-2031  |      18   |      22.7 |      22.1 |      26.1 |       15 |       18 |
| S        | 51-9061  |       9.9 |      13   |      13.8 |      17.9 |       10 |       13 |
| S        | 51-4121  |      19.4 |      24.1 |      24.1 |      27.9 |       17 |       20 |
| S        | 51-4081  |      11.1 |      16.5 |      14.8 |      20.2 |       10 |       14 |
| S        | 51-4041  |      11.9 |      17.5 |      15.2 |      21.1 |       10 |       15 |
| S        | 51-2028  |      20.1 |      23.7 |      24.7 |      27.8 |       17 |       20 |
| S        | 51-9161  |       7.6 |      12.3 |       9.7 |      14.8 |        6 |       10 |
| S        | 51-4072  |      17.7 |      21.2 |      21.3 |      24.7 |       14 |       17 |
| S        | 51-4122  |      15.6 |      19.5 |      21   |      24.9 |       15 |       18 |
| S        | 51-9124  |      17.3 |      21.6 |      22.9 |      27   |       17 |       20 |
