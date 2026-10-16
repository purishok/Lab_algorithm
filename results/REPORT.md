# Python V4 and S5 benchmark report

Assigned variant: V4, operation ratio 50:100:100, S5 group sort. Implementation uses Python's standard library.

Environment: Python 3.14.8, Darwin arm64.

## Task I: three approaches on 100,000 students

All approaches received the same precomputed 25,000-operation tape. Each shuffled 250-operation block contains exactly 50, 100, and 100 operations of types 1, 2, and 3. Emails and destination groups exist in the source. Setup and validation are outside timing. Final blocks can make elapsed time slightly exceed 10 seconds; normalized throughput accounts for that.

| Approach | Containers | Observed operations | Elapsed s | Operations / 10 s |
|---|---|---:|---:|---:|
| vector_scan | list, temporary group dict | 1,632 | 10.187 | 1,602 |
| aggregate_map | email dict, group aggregate dict | 7,168 | 10.022 | 7,152 |
| ranked_index | email/group dicts, tie sets, bounded max heaps | 9,874,560 | 10.000 | 9,874,532 |

**Winner: `ranked_index`.** List scanning costs O(n) for each operation. The aggregate map changes groups in expected O(1) and scans g groups for maximum queries. The ranked index uses dictionaries, exact `Fraction` average keys, tie sets, and bounded lazy heaps; updates are expected O(log g) amortized and returning k winning groups costs O(k) amortized. Maximum queries are 60% of this workload.

## Winner across ten database sizes

Five independent 10-second runs were made at each size. The operation tape was prepared before each run and reused cyclically. The initial database build and final validation are excluded. Operation latency is sampled every 128 executions of each type; stopwatch overhead and scheduling add noise.

| Students | Groups | Singleton share | Operations / 10 s, mean ± SD | Op 1 ns, mean ± SD | Op 2 ns, mean ± SD | Op 3 ns, mean ± SD | Slowest at n | Predicted op 2 ns | Estimated bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 100.0% | 3,959,219 ± 46,625 | 262.6 ± 7.7 | 4867.1 ± 52.4 | 1230.7 ± 48.2 | 2 | 4448.9 | 119,343 |
| 250 | 241 | 92.8% | 3,805,242 ± 124,737 | 259.9 ± 13.9 | 5154.6 ± 188.1 | 1195.9 ± 29.4 | 2 | 5172.4 | 273,539 |
| 500 | 466 | 86.4% | 3,717,338 ± 125,025 | 258.5 ± 12.4 | 5210.6 ± 179.3 | 1171.4 ± 45.1 | 2 | 5652.8 | 554,999 |
| 1,000 | 871 | 75.4% | 3,681,581 ± 75,634 | 258.2 ± 5.7 | 5406.8 ± 221.7 | 1193.8 ± 54.9 | 2 | 5896.9 | 1,044,022 |
| 2,500 | 1,802 | 50.1% | 3,587,757 ± 66,043 | 266.7 ± 50.1 | 5445.3 ± 308.2 | 1170.8 ± 29.2 | 2 | 5588.5 | 2,441,983 |
| 5,000 | 2,735 | 26.8% | 3,655,680 ± 140,362 | 249.6 ± 16.1 | 5401.6 ± 546.7 | 1158.2 ± 24.5 | 2 | 4732.2 | 4,278,552 |
| 10,000 | 3,566 | 8.8% | 4,496,499 ± 37,185 | 231.3 ± 6.3 | 4125.6 ± 461.6 | 1146.7 ± 16.7 | 2 | 3562.4 | 7,368,357 |
| 25,000 | 3,978 | 0.5% | 6,464,947 ± 67,505 | 220.9 ± 2.5 | 2261.9 ± 194.3 | 1256.2 ± 301.5 | 2 | 2208.9 | 16,204,060 |
| 50,000 | 3,999 | 0.0% | 8,597,773 ± 40,226 | 215.9 ± 2.6 | 1516.6 ± 100.4 | 1105.2 ± 11.0 | 2 | 1647.4 | 30,060,340 |
| 100,000 | 3,999 | 0.0% | 10,701,254 ± 206,718 | 216.1 ± 13.9 | 883.3 ± 108.9 | 1093.5 ± 5.5 | 3 | 1362.9 | 57,870,393 |

## Regression and memory

Let g(n) be the distinct-group count in the first n source rows, as tabulated above. Operation 2 has the highest mean latency across the ten sizes. T(n) = -225.8730 + 108.9984 log₂(g(n)) + 594.6253 [g(n)/n] log₂(g(n)) ns; R² = 0.9422.

The three terms model fixed work, heap height O(log g), and extra heap work weighted by group occupancy. The g/n factor is a heuristic for update churn, not an exact probability. Coefficients come from ordinary least squares over the ten operation-2 means. The table also identifies the slowest operation at each individual size; operation 3 is slightly slower at 100,000 rows. The negative intercept means the model should not be extrapolated outside the tested range. This is a dataset-specific descriptive fit and does not prove asymptotic growth. Distinct groups saturate near 4,000, so update cost need not grow monotonically with n.

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
