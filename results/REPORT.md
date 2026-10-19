# Python V4 and S5 benchmark report

Assigned variant: V4, operation ratio 50:100:100, S5 group sort. Implementation uses Python's standard library.

Environment: Python 3.14.8, Darwin arm64.

## Task I: three approaches on 100,000 students

All approaches received the same precomputed 25,000-operation tape. Each shuffled 250-operation block contains exactly 50, 100, and 100 operations of types 1, 2, and 3. Emails and destination groups exist in the source. The first half makes random moves to a different group; the second half reverses those moves in reverse order, interleaved with randomly ordered queries. Every move changes the group, and each complete tape restores the initial database, so cyclic replay cannot turn updates into no-ops. This is a reversible workload, not a stream of independent updates. Setup and validation are outside timing. Final blocks can make elapsed time slightly exceed 10 seconds; normalized throughput accounts for that.

| Approach | Containers | Observed operations | Elapsed s | Operations / 10 s |
|---|---|---:|---:|---:|
| vector_scan | list, temporary group dict | 1,632 | 10.166 | 1,605 |
| aggregate_map | email dict, group aggregate dict | 7,072 | 10.021 | 7,057 |
| ranked_index | email/group dicts, tie sets, bounded max heaps | 3,033,920 | 10.000 | 3,033,901 |

**Winner: `ranked_index`.** List scanning costs O(n) for each operation. The aggregate map changes groups in expected O(1) and scans g groups for maximum queries. The ranked index uses dictionaries, exact `Fraction` average keys, tie sets, and bounded lazy heaps; updates are expected O(log g) amortized and returning k winning groups costs O(k) amortized. Maximum queries are 60% of this workload.

## Winner across ten database sizes

Five independent 10-second runs were made at each size. The operation tape was prepared before each run and reused cyclically. The initial database build and final validation are excluded. Operation latency is sampled every 128 executions of each type; stopwatch overhead and scheduling add noise.

| Students | Groups | Singleton share | Operations / 10 s, mean ± SD | Op 1 ns, mean ± SD | Op 2 ns, mean ± SD | Op 3 ns, mean ± SD | Slowest at n | Predicted op 2 ns | Estimated bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 100.0% | 4,000,098 ± 85,908 | 259.6 ± 13.1 | 4814.0 ± 173.3 | 1230.1 ± 49.6 | 2 | 4499.1 | 119,343 |
| 250 | 241 | 92.8% | 3,895,508 ± 29,454 | 259.8 ± 2.6 | 5126.5 ± 109.0 | 1151.0 ± 13.1 | 2 | 4943.6 | 273,539 |
| 500 | 466 | 86.4% | 3,841,030 ± 31,474 | 253.6 ± 4.8 | 5146.9 ± 310.4 | 1161.5 ± 50.9 | 2 | 5281.3 | 554,999 |
| 1,000 | 871 | 75.4% | 3,805,235 ± 11,534 | 258.9 ± 5.7 | 5178.3 ± 250.7 | 1149.1 ± 44.4 | 2 | 5627.0 | 1,044,022 |
| 2,500 | 1,802 | 50.1% | 3,610,760 ± 5,413 | 595.1 ± 772.3 | 5361.9 ± 146.8 | 1142.6 ± 28.0 | 2 | 6107.5 | 2,441,983 |
| 5,000 | 2,735 | 26.8% | 3,417,520 ± 5,129 | 247.1 ± 4.6 | 6001.1 ± 301.5 | 1197.4 ± 57.7 | 2 | 6502.1 | 4,278,552 |
| 10,000 | 3,566 | 8.8% | 2,648,586 ± 585,406 | 300.8 ± 73.0 | 7569.4 ± 1792.4 | 1427.0 ± 298.3 | 2 | 6932.5 | 7,368,357 |
| 25,000 | 3,978 | 0.5% | 2,388,292 ± 411,512 | 314.2 ± 46.8 | 9279.1 ± 2211.8 | 1555.4 ± 328.8 | 2 | 7558.2 | 16,204,060 |
| 50,000 | 3,999 | 0.0% | 2,751,028 ± 74,363 | 285.4 ± 66.8 | 7914.9 ± 1549.9 | 1241.8 ± 17.2 | 2 | 8049.8 | 30,060,340 |
| 100,000 | 3,999 | 0.0% | 2,834,040 ± 80,074 | 269.7 ± 11.4 | 7651.7 ± 1122.5 | 1228.1 ± 79.3 | 2 | 8542.6 | 57,870,393 |

## Regression and memory

Let g(n) be the distinct-group count in the first n source rows, as tabulated above. Operation 2 has the highest mean latency across the ten sizes. T(n) = 2308.1417 + -163.0266 log₂(g(n)) + 492.7941 log₂(n) ns; R² = 0.7569.

The basis functions are f1(n)=1, f2(n)=log₂(g(n)), and f3(n)=log₂(n). They represent expected constant-time dictionary/set work, amortized heap maintenance, and exact-average normalization: Fraction reduces integer rating sums and counts using GCD, whose Euclidean algorithm takes O(log n) arithmetic steps because ratings are bounded and sums/counts are O(n). This separates structural work from integer normalization; it is an explanatory cost model, not a full bit-complexity bound. Here g(n) is the initial group count and an upper bound during these moves; empty groups may disappear temporarily. Coefficients come from ordinary least squares over the ten operation-2 means. The table also identifies the slowest operation at each individual size. The model should not be extrapolated outside the tested range. This is a dataset-specific descriptive fit and does not prove asymptotic growth. Distinct groups saturate near 4,000, so update cost need not grow monotonically with n.

Memory is `deep_sizeof(database)` before timing: `sys.getsizeof` sums reachable lists, dictionaries, sets, tuples, heap entries, student objects, strings, integers, and fractions once each. Immutable strings shared with the source objects are included because the database references them. The separate source list, Python interpreter, allocator overhead, source CSV file, and prepared operation tape are excluded; this is not process RSS.

![Slowest operation and fit](slowest_regression.svg)

![Mixed workload throughput](throughput.svg)

## Task II: S5 sorting by group

`standard` uses Python's `sorted` with the group key, O(n log n). `radix` builds a dictionary of group buckets, uses five stable counting passes to order the distinct `AAA-00` keys, then concatenates buckets: O(n + 5(g + 256)). The timed interval includes all helper structures made by each sort and excludes CSV writing. Each size and method has five repetitions; method order alternates.

| Students | Standard ms, mean ± SD | Radix ms, mean ± SD | Faster method |
|---:|---:|---:|---|
| 100 | 0.0075 ± 0.0025 | 0.1075 ± 0.0083 | standard |
| 250 | 0.0201 ± 0.0046 | 0.2223 ± 0.0087 | standard |
| 500 | 0.0428 ± 0.0091 | 0.4387 ± 0.0091 | standard |
| 1,000 | 0.0921 ± 0.0127 | 0.7874 ± 0.0046 | standard |
| 2,500 | 0.2526 ± 0.0163 | 1.6629 ± 0.0486 | standard |
| 5,000 | 0.5262 ± 0.0160 | 2.6026 ± 0.0256 | standard |
| 10,000 | 1.1621 ± 0.0181 | 3.6134 ± 0.0358 | standard |
| 25,000 | 3.2699 ± 0.0390 | 4.8468 ± 0.1366 | standard |
| 50,000 | 7.0119 ± 0.0737 | 6.2914 ± 0.1812 | radix |
| 100,000 | 14.7018 ± 0.1148 | 9.9429 ± 0.3269 | radix |

![S5 sort comparison](s5_sort.svg)

The full sorted outputs are `s5_standard.csv` and `s5_radix.csv`. Independent checks confirm ascending groups and exact preservation of all input fields and email identifiers; tie order is unspecified.

## Defense notes

All three designs pass differential tests after randomized group changes, including ties and disappearing groups. The ranked index rebuilds stale heaps periodically to bound their memory. Python dictionaries use randomized string hashing but do not offer deterministic worst-case lookup time. For adversarial input, replace email and group dictionaries with a balanced search tree for O(log n) lookup, validate sizes and formats, and paginate large tied results.
