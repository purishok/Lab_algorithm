# V4 benchmark results

Variant: V4, ratio 50:100:100. Each row averages five independent 10 second runs. The operation tape contains 25,000 randomly shuffled, preselected operations and repeats cyclically. Student emails and destination groups are chosen from existing values before timing. The initial index build and the final validation are outside the timed interval.

| Students | Groups | Singleton share | Operations / 10 s, mean ± SD | Op 1 ns, mean ± SD | Op 2 ns, mean ± SD | Op 3 ns, mean ± SD | Slowest | Predicted T(n), ns | Estimated bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 100.0% | 47,767,962 ± 339,107 | 75.6 ± 2.2 | 460.2 ± 5.6 | 36.4 ± 3.0 | 2 | 542.5 | 61,680 |
| 250 | 241 | 92.8% | 41,790,669 ± 238,659 | 74.5 ± 5.1 | 538.9 ± 3.1 | 34.4 ± 0.7 | 2 | 590.6 | 151,318 |
| 500 | 466 | 86.4% | 37,099,725 ± 168,552 | 75.9 ± 5.4 | 609.3 ± 3.5 | 33.7 ± 0.3 | 2 | 625.8 | 298,664 |
| 1,000 | 871 | 75.4% | 32,206,234 ± 194,784 | 80.7 ± 2.5 | 699.5 ± 7.7 | 33.5 ± 0.6 | 2 | 658.8 | 582,896 |
| 2,500 | 1,802 | 50.1% | 27,219,354 ± 143,260 | 73.3 ± 7.5 | 847.5 ± 9.2 | 32.5 ± 0.4 | 2 | 695.3 | 1,361,346 |
| 5,000 | 2,735 | 26.8% | 25,862,554 ± 233,513 | 80.2 ± 10.0 | 893.1 ± 21.3 | 32.9 ± 0.5 | 2 | 711.3 | 2,488,978 |
| 10,000 | 3,566 | 8.8% | 31,324,365 ± 434,104 | 69.9 ± 9.8 | 740.0 ± 24.9 | 32.4 ± 0.8 | 2 | 705.9 | 4,520,756 |
| 25,000 | 3,978 | 0.5% | 53,142,528 ± 1,884,999 | 55.9 ± 28.6 | 422.3 ± 15.6 | 31.2 ± 1.1 | 2 | 627.0 | 10,047,052 |
| 50,000 | 3,999 | 0.0% | 81,925,325 ± 2,955,164 | 40.2 ± 10.8 | 273.8 ± 18.6 | 30.9 ± 0.4 | 2 | 450.5 | 19,144,630 |
| 100,000 | 3,999 | 0.0% | 108,208,538 ± 6,692,897 | 75.7 ± 22.5 | 183.5 ± 7.5 | 31.6 ± 1.0 | 2 | 60.4 | 37,345,958 |

## Regression

T(n) = 295.4215 + 37.3230 log₂(n) − 0.008549451 n nanoseconds; R² = 0.6862.

The basis reflects constant-time work, ordered-set updates with O(log g) complexity for g groups (bounded by n), and the O(n) worst case of the email hash lookup under collisions. It is fitted to the slowest mean operation at each database size. This is a weak descriptive fit: the linear coefficient is negative and the model predicts the 100,000-student case poorly. Group count saturates near 4,000 while the share of singleton groups falls to zero, changing the cost of updates that remove and recreate groups. The benchmark cannot establish an asymptotic growth law from these ten points. Latencies are sampled every 128 operations, so timer overhead and operating-system scheduling contribute to measured variance.

## Memory method

`estimated_bytes()` sums vector capacity, string capacities, hash buckets and approximate nodes, and ordered-set nodes. This is a reproducible approximation, not process RSS: allocator metadata, code, stack, the prepared operation tape, and source CSV are excluded. Short strings may be stored inline, so counting their capacities can overstate heap use.

![Slowest operation and fit](slowest_regression.svg)

![Throughput](throughput.svg)
