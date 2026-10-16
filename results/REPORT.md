# V4 benchmark results

Variant: V4, ratio 50:100:100. Each row averages five independent 10 second runs. The operation tape contains 25,000 randomly shuffled, preselected operations and repeats cyclically. Student emails and destination groups are chosen from existing values before timing. The initial index build and the final validation are outside the timed interval.

| Students | Groups | Singleton share | Operations / 10 s, mean ± SD | Op 1 ns, mean ± SD | Op 2 ns, mean ± SD | Op 3 ns, mean ± SD | Slowest | Predicted T(n), ns | Estimated bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 100.0% | 47,767,962 ± 339,107 | 75.6 ± 2.2 | 460.2 ± 5.6 | 36.4 ± 3.0 | 2 | 352.1 | 61,680 |
| 250 | 241 | 92.8% | 41,790,669 ± 238,659 | 74.5 ± 5.1 | 538.9 ± 3.1 | 34.4 ± 0.7 | 2 | 562.3 | 151,318 |
| 500 | 466 | 86.4% | 37,099,725 ± 168,552 | 75.9 ± 5.4 | 609.3 ± 3.5 | 33.7 ± 0.3 | 2 | 710.2 | 298,664 |
| 1,000 | 871 | 75.4% | 32,206,234 ± 194,784 | 80.7 ± 2.5 | 699.5 ± 7.7 | 33.5 ± 0.6 | 2 | 817.4 | 582,896 |
| 2,500 | 1,802 | 50.1% | 27,219,354 ± 143,260 | 73.3 ± 7.5 | 847.5 ± 9.2 | 32.5 ± 0.4 | 2 | 849.4 | 1,361,346 |
| 5,000 | 2,735 | 26.8% | 25,862,554 ± 233,513 | 80.2 ± 10.0 | 893.1 ± 21.3 | 32.9 ± 0.5 | 2 | 761.7 | 2,488,978 |
| 10,000 | 3,566 | 8.8% | 31,324,365 ± 434,104 | 69.9 ± 9.8 | 740.0 ± 24.9 | 32.4 ± 0.8 | 2 | 608.1 | 4,520,756 |
| 25,000 | 3,978 | 0.5% | 53,142,528 ± 1,884,999 | 55.9 ± 28.6 | 422.3 ± 15.6 | 31.2 ± 1.1 | 2 | 408.6 | 10,047,052 |
| 50,000 | 3,999 | 0.0% | 81,925,325 ± 2,955,164 | 40.2 ± 10.8 | 273.8 ± 18.6 | 30.9 ± 0.4 | 2 | 321.4 | 19,144,630 |
| 100,000 | 3,999 | 0.0% | 108,208,538 ± 6,692,897 | 75.7 ± 22.5 | 183.5 ± 7.5 | 31.6 ± 1.0 | 2 | 276.9 | 37,345,958 |

## Regression

Let g(n) be the number of distinct groups in the first n records (shown in the table). T(n) = -886.9939 + 93.5567 log₂(g(n)) + 92.9470 [g(n)/n] log₂(g(n)) nanoseconds; R² = 0.8358.

The three basis functions represent fixed work, O(log g) balanced-tree updates, and extra O(log g) work weighted by group occupancy. The factor g/n is a coarse proxy for how often a move empties or recreates a group; it is not an exact probability. The fit is descriptive over this dataset, with a negative intercept outside the tested range. It does not prove asymptotic behavior. Group count saturates near 4,000 while singleton share falls to zero, so measured update time is not monotone in n. Latencies are sampled every 128 operations; timer overhead and operating-system scheduling contribute to variance.

## Memory method

`estimated_bytes()` sums vector capacity, string capacities, hash buckets and approximate nodes, and ordered-set nodes. This is a reproducible approximation, not process RSS: allocator metadata, code, stack, the prepared operation tape, and source CSV are excluded. Short strings may be stored inline, so counting their capacities can overstate heap use.

![Slowest operation and fit](slowest_regression.svg)

![Throughput](throughput.svg)

## Three V4 approaches on 100,000 students

All approaches used the same preselected 25,000-operation tape, shuffled in 250-operation blocks containing exactly 50:100:100 operations. Each approach ran for 10 seconds; reported throughput is normalized to exactly 10 seconds to account for the final block. Setup and post-run validation are excluded.

| Approach | Main containers | Operations observed | Elapsed, s | Operations / 10 s |
|---|---|---:|---:|---:|
| vector_scan | vector, temporary hash aggregates | 9,728 | 10.039 | 9,690 |
| aggregate_map | email hash + ordered group map | 557,056 | 10.001 | 557,021 |
| ranked_sets | email hash + two ordered group sets | 102,235,968 | 10.000 | 102,235,907 |

**Winner: `ranked_sets`.** Vector queries and email changes scan n students: O(n) work per operation. The aggregate map finds an email in expected O(1), changes two groups in O(log g), and scans g group aggregates for each maximum query. Ranked sets find an email in expected O(1), update two ranking sets in O(log g), and return k tied groups in O(k). The weighted workload has 60% maximum queries, explaining the large ranked-set advantage at 100,000 rows. All three approaches pass differential tests after group changes.

## S5: sorting by group

`standard` sorts student records using `std::sort` and group comparisons, O(n log n). `radix` uses five stable counting passes over the nonconstant characters of the fixed `AAA-00` group key, then reorders records, O(5(n + 256)). The radix timing includes index arrays and all counting passes. Both methods sort a copied input; copying and CSV writing are outside the measured sort time. Each point uses five repetitions; method order alternates across repetitions.

| Students | Standard ms, mean ± SD | Radix ms, mean ± SD | Faster method |
|---:|---:|---:|---|
| 100 | 0.0075 ± 0.0080 | 0.0023 ± 0.0008 | radix |
| 250 | 0.0181 ± 0.0025 | 0.0063 ± 0.0017 | radix |
| 500 | 0.0320 ± 0.0101 | 0.0105 ± 0.0045 | radix |
| 1,000 | 0.0707 ± 0.0122 | 0.0257 ± 0.0092 | radix |
| 2,500 | 0.2020 ± 0.0124 | 0.0593 ± 0.0108 | radix |
| 5,000 | 0.4579 ± 0.0146 | 0.1160 ± 0.0186 | radix |
| 10,000 | 1.0113 ± 0.0395 | 0.2449 ± 0.0377 | radix |
| 25,000 | 2.6646 ± 0.0495 | 0.6388 ± 0.0949 | radix |
| 50,000 | 5.2760 ± 0.1109 | 1.3865 ± 0.2144 | radix |
| 100,000 | 10.3222 ± 0.1462 | 4.5381 ± 0.6170 | radix |

![S5 sorting comparison](s5_sort.svg)

The full 100,000-row outputs are `s5_standard.csv` and `s5_radix.csv`. An independent CSV check confirmed that each has all source email identifiers exactly once and is ordered by `m_group`. Their within-group row order may differ, as the assignment permits.

## Defense notes

The ranked-set design is rational for the given 50:100:100 mix because two of the three frequent operations ask for maxima. Differential tests check all query answers after 1,000 random changes; the timed run also validates index consistency afterward. With untrusted inputs, both email and group hash tables can suffer collision attacks: use ordered maps for both to guarantee logarithmic lookups, keep balanced group rankings, validate input sizes, and paginate a potentially huge tie result. CSV parsing and operation generation happen before timing.
